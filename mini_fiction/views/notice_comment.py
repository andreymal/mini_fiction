#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for, g, jsonify
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.forms.comment import CommentForm
from mini_fiction.models import Notice, NoticeComment
from mini_fiction.validation import ValidationError

bp = Blueprint('notice_comment', __name__)


@bp.route('/notice/<int:notice_id>/comment/add/', methods=('GET', 'POST'))
@db_session
def add(notice_id):
    user = current_user._get_current_object()
    notice = Notice.get(id=notice_id)
    if not notice:
        abort(404)

    if request.args.get('parent') and request.args['parent'].isdigit():
        parent = NoticeComment.get(notice=notice.id, local_id=int(request.args['parent']), deleted=False)
        if not parent:
            abort(404)
    else:
        parent = None

    if parent and not parent.bl.can_answer_by(user):
        abort(403)
    elif not notice.bl.can_comment_by(user):
        abort(403)

    form = CommentForm(request.form)
    if form.validate_on_submit():
        data = dict(form.data)
        if request.form.get('parent'):
            data['parent'] = request.form['parent']
        try:
            comment = NoticeComment.bl.create(notice, user, request.remote_addr, data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            if g.is_ajax:
                return jsonify({
                    'success': True,
                    'notice': notice.name,
                    'comment': comment.local_id,
                    'global_id': comment.id,
                    'link': comment.bl.get_permalink(),
                    'html': render_template(
                        'includes/comments_tree.html',
                        notice=notice,
                        comments_tree_list=[[comment, False]],
                    )
                })
            else:
                return redirect(comment.bl.get_permalink())

    if g.is_ajax and (form.errors or form.non_field_errors):
        errors = sum(form.errors.values(), []) + form.non_field_errors
        errors = '; '.join(str(x) for x in errors)
        return jsonify({'success': False, 'error': errors})

    data = {
        'page_title': gettext('Add new comment'),
        'form': form,
        'notice': notice,
        'parent_comment': parent,
        'edit': False,
    }
    return render_template('notices/comment_work.html', **data)


@bp.route('/notice/<int:notice_id>/comment/<int:local_id>/edit/', methods=('GET', 'POST'))
@db_session
def edit(notice_id, local_id):
    user = current_user._get_current_object()
    comment = NoticeComment.get(notice=notice_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)
    if not comment.bl.can_update_by(user):
        abort(403)

    form = CommentForm(request.form, data={'text': comment.text})
    if form.validate_on_submit():
        try:
            comment.bl.update(user, request.remote_addr, form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Edit comment'),
        'form': form,
        'notice': comment.notice,
        'comment': comment,
        'edit': True,
    }
    return render_template('notices/comment_work.html', **data)


@bp.route('/notice/<int:notice_id>/comment/<int:local_id>/delete/', methods=('GET', 'POST'))
@db_session
def delete(notice_id, local_id):
    user = current_user._get_current_object()
    comment = NoticeComment.get(notice=notice_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)
    if not comment.bl.can_delete_or_restore_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.delete(user)
        if g.is_ajax:
            return jsonify({
                'success': True,
                'notice': notice_id,
                'comment': local_id,
                'deleted': comment.deleted,
                'html': render_template('includes/comment_single.html', comment=comment),
            })
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Confirm delete comment'),
        'notice': comment.notice,
        'comment': comment,
    }
    if g.is_ajax:
        html = render_template('notices/comment_delete_ajax.html', **data)
        return jsonify({'page_content': {'modal': True, 'content': html}})
    else:
        return render_template('notices/comment_delete.html', **data)


@bp.route('/notice/<int:notice_id>/comment/<int:local_id>/restore/', methods=('GET', 'POST'))
@db_session
def restore(notice_id, local_id):
    user = current_user._get_current_object()
    comment = NoticeComment.get(notice=notice_id, local_id=local_id, deleted=True)
    if not comment:
        abort(404)
    if not comment.bl.can_delete_or_restore_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.restore(user)
        if g.is_ajax:
            return jsonify({
                'success': True,
                'notice': notice_id,
                'comment': local_id,
                'deleted': comment.deleted,
                'html': render_template('includes/comment_single.html', comment=comment),
            })
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Confirm restore comment'),
        'notice': comment.notice,
        'comment': comment,
    }
    if g.is_ajax:
        html = render_template('notices/comment_restore_ajax.html', **data)
        return jsonify({'page_content': {'modal': True, 'content': html}})
    else:
        return render_template('notices/comment_restore.html', **data)


@bp.route('/notice/<int:notice_id>/comment/<int:local_id>/vote/', methods=('POST',))
@db_session
def vote(notice_id, local_id):
    user = current_user._get_current_object()
    comment = NoticeComment.get(notice=notice_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    try:
        value = int(request.form.get('value', 0))
    except ValueError:
        value = 0

    try:
        comment.bl.vote(user, value)
    except ValidationError as exc:
        errors = sum(exc.errors.values(), [])
        return jsonify({'success': False, 'error': '; '.join(str(x) for x in errors)})
    return jsonify({
        'success': True,
        'vote_total': comment.vote_total,
        'vote_count': comment.vote_count,
        'html': render_template('includes/comment_vote.html', comment=comment)
    })


@bp.route('/ajax/notice/<int:notice_id>/comments/page/<int:page>/')
@db_session
def ajax(notice_id, page):
    notice = Notice.get(id=notice_id)
    if not notice:
        abort(404)

    per_page = current_app.config['COMMENTS_COUNT']['page']
    maxdepth = None if request.args.get('fulltree') == '1' else 2

    comments_count, paged, comments_tree_list = notice.bl.paginate_comments(page, per_page, maxdepth)
    if not comments_tree_list and paged.number != 1:
        abort(404)

    comment_spoiler_threshold = current_app.config['COMMENT_SPOILER_THRESHOLD']
    data = {
        'notice': notice,
        'comments_tree_list': comments_tree_list,
        'num_pages': paged.num_pages,
        'page_current': page,
        'page_obj': paged,
        'comment_spoiler_threshold': comment_spoiler_threshold,
    }

    return jsonify({
        'success': True,
        'link': url_for('notices.show', name=notice.name, comments_page=page),
        'comments_count': comments_count,
        'comments_tree': render_template('includes/comments_tree.html', **data),
        'pagination': render_template('notices/comments_pagination.html', **data),
    })


@bp.route('/ajax/notice/<int:notice_id>/comments/tree/<int:local_id>/')
@db_session
def ajax_tree(notice_id, local_id):
    notice = Notice.get(id=notice_id)
    if not notice:
        abort(404)

    comment = notice.comments.select(lambda x: x.local_id == local_id).first()
    if not comment:
        abort(404)

    # Проще получить все комментарии и потом выбрать оттуда нужные
    comments_tree_list = notice.bl.get_comments_tree_list(
        maxdepth=None,
        root_offset=comment.root_order,
        root_count=1,
    )

    # Ищем начало нужной ветки
    start = None
    for i, x in enumerate(comments_tree_list):
        if x[0].local_id == comment.local_id:
            start = i
            break
    if start is None:
        abort(404)

    tree = None
    # Ищем конец ветки
    for i, x in enumerate(comments_tree_list[start + 1:], start + 1):
        if x[0].tree_depth == comment.tree_depth + 1:
            assert x[0].parent.id == comment.id  # debug
        if x[0].tree_depth <= comment.tree_depth:
            tree = comments_tree_list[start + 1:i]
            break
    # Если ветка оказалось концом комментариев
    if tree is None:
        tree = comments_tree_list[start + 1:]

    comment_spoiler_threshold = current_app.config['COMMENT_SPOILER_THRESHOLD']
    data = {
        'notice': notice,
        'comments_tree_list': tree,
        'comment_spoiler_threshold': comment_spoiler_threshold,
    }

    return jsonify({
        'success': True,
        'tree_for': comment.local_id,
        'comments_tree': render_template('includes/comments_tree.html', **data),
    })
