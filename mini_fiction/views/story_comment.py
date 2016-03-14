#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for, g, jsonify
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.forms.comment import CommentForm
from mini_fiction.models import Story, StoryComment, CoAuthorsStory
from mini_fiction.utils.misc import Paginator
from mini_fiction.validation import ValidationError

bp = Blueprint('story_comment', __name__)


@bp.route('/story/<int:story_id>/comment/add/', methods=('GET', 'POST'))
@db_session
def add(story_id):
    user = current_user._get_current_object()
    story = Story.get(id=story_id)
    if not story:
        abort(404)

    if request.args.get('parent') and request.args['parent'].isdigit():
        parent = StoryComment.get(story=story_id, local_id=int(request.args['parent']), deleted=False)
        if not parent:
            abort(404)
    else:
        parent = None

    if parent and not parent.bl.can_answer_by(user):
        abort(403)
    elif not story.bl.can_comment_by(user):
        abort(403)

    form = CommentForm(request.form)
    if form.validate_on_submit():
        data = dict(form.data)
        if request.form.get('parent'):
            data['parent'] = request.form['parent']
        try:
            comment = StoryComment.bl.create(story, user, request.remote_addr, data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            if g.is_ajax:
                return jsonify({
                    'success': True,
                    'story': story.id,
                    'comment': comment.local_id,
                    'global_id': comment.id,
                    'link': comment.bl.get_permalink(),
                    'html': render_template(
                        'includes/comments_tree.html',
                        story=story,
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
        'story': story,
        'parent_comment': parent,
        'edit': False,
    }
    return render_template('story_comment_work.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:local_id>/edit/', methods=('GET', 'POST'))
@db_session
def edit(story_id, local_id):
    user = current_user._get_current_object()
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=False)
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
        'story': comment.story,
        'comment': comment,
        'edit': True,
    }
    return render_template('story_comment_work.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:local_id>/delete/', methods=('GET', 'POST'))
@db_session
def delete(story_id, local_id):
    user = current_user._get_current_object()
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=False)
    if not comment:
        abort(404)
    if not comment.bl.can_delete_or_restore_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.delete(user)
        if g.is_ajax:
            return jsonify({
                'success': True,
                'story': story_id,
                'comment': local_id,
                'deleted': comment.deleted,
                'html': render_template('includes/comment_single.html', comment=comment),
            })
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Confirm delete comment'),
        'story': comment.story,
        'comment': comment,
    }
    if g.is_ajax:
        html = render_template('includes/ajax/story_comment_delete.html', **data)
        return jsonify({'page_content': {'modal': True, 'content': html}})
    else:
        return render_template('story_comment_delete.html', **data)


@bp.route('/story/<int:story_id>/comment/<int:local_id>/restore/', methods=('GET', 'POST'))
@db_session
def restore(story_id, local_id):
    user = current_user._get_current_object()
    comment = StoryComment.get(story=story_id, local_id=local_id, deleted=True)
    if not comment:
        abort(404)
    if not comment.bl.can_delete_or_restore_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.restore(user)
        if g.is_ajax:
            return jsonify({
                'success': True,
                'story': story_id,
                'comment': local_id,
                'deleted': comment.deleted,
                'html': render_template('includes/comment_single.html', comment=comment),
            })
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Confirm restore comment'),
        'story': comment.story,
        'comment': comment,
    }
    if g.is_ajax:
        html = render_template('includes/ajax/story_comment_restore.html', **data)
        return jsonify({'page_content': {'modal': True, 'content': html}})
    else:
        return render_template('story_comment_restore.html', **data)


@bp.route('/ajax/story/<int:story_id>/comments/page/<int:page>/')
@db_session
def ajax(story_id, page):
    story = Story.get(id=story_id)
    if not story:
        abort(404)
    if not story.bl.has_access(current_user):
        abort(403)

    per_page = current_app.config['COMMENTS_COUNT']['page']
    maxdepth = None if request.args.get('fulltree') == '1' else 2

    comments_count, paged, comments_tree_list = story.bl.paginate_comments(page, per_page, maxdepth)
    if not comments_tree_list and paged.number != 1:
        abort(404)
    if request.args.get('last_comment') and request.args['last_comment'].isdigit():
        last_viewed_comment = int(request.args['last_comment'])
    else:
        last_viewed_comment = story.bl.last_viewed_comment_by(current_user)

    data = {
        'story': story,
        'comments_tree_list': comments_tree_list,
        'last_viewed_comment': last_viewed_comment,
        'num_pages': paged.num_pages,
        'page_current': page,
        'page_obj': paged,
    }

    return jsonify({
        'success': True,
        'link': url_for('story.view', pk=story.id, comments_page=page),
        'comments_count': comments_count,
        'comments_tree': render_template('includes/comments_tree.html', **data),
        'pagination': render_template('includes/comments_pagination_story.html', **data),
    })


@bp.route('/ajax/story/<int:story_id>/comments/tree/<int:local_id>/')
@db_session
def ajax_tree(story_id, local_id):
    story = Story.get(id=story_id)
    if not story:
        abort(404)
    if not story.bl.has_access(current_user):
        abort(403)

    comment = story.comments.select(lambda x: x.local_id == local_id).first()
    if not comment:
        abort(404)

    # Проще получить все комментарии и потом выбрать оттуда нужные
    comments_tree_list = story.bl.get_comments_tree_list(
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

    if request.args.get('last_comment') and request.args['last_comment'].isdigit():
        last_viewed_comment = int(request.args['last_comment'])
    else:
        last_viewed_comment = story.bl.last_viewed_comment_by(current_user)

    data = {
        'story': story,
        'comments_tree_list': tree,
        'last_viewed_comment': last_viewed_comment,
    }

    return jsonify({
        'success': True,
        'tree_for': comment.local_id,
        'comments_tree': render_template('includes/comments_tree.html', **data),
    })
