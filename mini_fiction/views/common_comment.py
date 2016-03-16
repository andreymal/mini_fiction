#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app, request, g, jsonify, abort, redirect, render_template
from flask_login import current_user
from flask_babel import gettext

from mini_fiction.forms.comment import CommentForm
from mini_fiction.validation import ValidationError


def build_comment_tree_response(comment, target_attr, target):
    html = render_template(
        'includes/comments_tree.html',
        **{
            target_attr: target,
            'comments_tree_list': [[comment, False]]
        },
    )
    return jsonify({
        'success': True,
        target_attr: target.id,
        'comment': comment.local_id,
        'global_id': comment.id,
        'deleted': comment.deleted,
        'link': comment.bl.get_permalink(),
        'html': html
    })


def build_comment_response(comment, target_attr, target):
    html = render_template('includes/comment_single.html', comment=comment)
    return jsonify({
        'success': True,
        target_attr: target.id,
        'comment': comment.local_id,
        'global_id': comment.id,
        'deleted': comment.deleted,
        'link': comment.bl.get_permalink(),
        'html': html
    })


def add(target_attr, target, template, template_ajax=None, template_ajax_modal=False):
    user = current_user._get_current_object()

    # Получаем комментарий, ответом на который является создаваемый
    parent_id = request.form.get('parent') or request.args.get('parent')
    if parent_id and parent_id.isdigit() and parent_id != '0':
        parent_id = int(parent_id)
        parent = target.comments.select(lambda c: c.local_id == parent_id and not c.deleted).first()
        if not parent:
            abort(404)
    else:
        parent = None

    # Проверки доступа (дублируются в Comment.bl.create, здесь просто для user-friendly)
    if parent and not parent.bl.can_answer_by(user):
        abort(403)
    elif not target.bl.can_comment_by(user):
        abort(403)

    form = CommentForm()
    if form.validate_on_submit():
        # Обработка POST-запроса
        data = dict(form.data)

        # Если родительский комментарий указан через query string, а не форму
        if parent:
            data['parent'] = parent.local_id

        # Собственно создание
        try:
            comment = target.bl.create_comment(user, request.remote_addr, data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            if g.is_ajax:
                # Для AJAX отвечаем просто html-кодом комментария и всякой технической инфой
                return build_comment_tree_response(comment, target_attr, target)
            else:
                # Иначе редиректим на страницу с комментарием
                # (FIXME: что не всегда хорошо, потому что коммент может оказаться в скрытой ветке)
                return redirect(comment.bl.get_permalink())

    # При ошибках с AJAX не церемонимся и просто отсылаем строку с ошибками
    # (на фронтенде будет всплывашка в углу)
    if g.is_ajax and (form.errors or form.non_field_errors):
        errors = sum(form.errors.values(), []) + form.non_field_errors
        errors = '; '.join(str(x) for x in errors)
        return jsonify({'success': False, 'error': errors})

    # Здесь код рисования полноценной страницы с формой
    data = {
        'page_title': gettext('Add new comment'),
        'form': form,
        target_attr: target,
        'parent_comment': parent,
        'edit': False,
    }

    if g.is_ajax and template_ajax:
        html = render_template(template_ajax, **data)
        return jsonify({'page_content': {'modal': template_ajax_modal, 'content': html}})
    else:
        return render_template(template, **data)


def edit(target_attr, comment, template, template_ajax=None, template_ajax_modal=False):
    user = current_user._get_current_object()
    target = getattr(comment, target_attr)

    if not comment.bl.can_update_by(user):
        abort(403)

    extra_ajax = g.is_ajax and request.form.get('extra_ajax') == '1'
    form = CommentForm(request.form, data={'text': comment.text})
    if form.validate_on_submit():
        try:
            comment.bl.update(user, request.remote_addr, form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            if extra_ajax:
                return build_comment_response(comment, target_attr, target)
            else:
                return redirect(comment.bl.get_permalink())

    if extra_ajax and (form.errors or form.non_field_errors):
        errors = sum(form.errors.values(), []) + form.non_field_errors
        errors = '; '.join(str(x) for x in errors)
        return jsonify({'success': False, 'error': errors})

    data = {
        'page_title': gettext('Edit comment'),
        'form': form,
        target_attr: target,
        'comment': comment,
        'edit': True,
    }

    if g.is_ajax and template_ajax:
        html = render_template(template_ajax, **data)
        return jsonify({'page_content': {'modal': template_ajax_modal, 'content': html}})
    else:
        return render_template(template, **data)


def delete(target_attr, comment, template, template_ajax=None, template_ajax_modal=False):
    user = current_user._get_current_object()
    target = getattr(comment, target_attr)

    if not comment.bl.can_delete_or_restore_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.delete(user)  # из БД не удаляется!
        if g.is_ajax:
            return build_comment_response(comment, target_attr, target)
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Confirm delete comment'),
        target_attr: target,
        'comment': comment,
        'comment_delete': True,
    }

    if g.is_ajax and template_ajax:
        html = render_template(template_ajax, **data)
        return jsonify({'page_content': {'modal': template_ajax_modal, 'content': html}})
    else:
        return render_template(template, **data)


def restore(target_attr, comment, template, template_ajax=None, template_ajax_modal=False):
    user = current_user._get_current_object()
    target = getattr(comment, target_attr)

    if not comment.bl.can_delete_or_restore_by(user):
        abort(403)

    if request.method == 'POST':
        comment.bl.restore(user)
        if g.is_ajax:
            return build_comment_response(comment, target_attr, target)
        else:
            return redirect(comment.bl.get_permalink())

    data = {
        'page_title': gettext('Confirm restore comment'),
        target_attr: target,
        'comment': comment,
        'comment_restore': True,
    }

    if g.is_ajax and template_ajax:
        html = render_template(template_ajax, **data)
        return jsonify({'page_content': {'modal': template_ajax_modal, 'content': html}})
    else:
        return render_template(template, **data)


def vote(target_attr, comment):
    user = current_user._get_current_object()

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


def ajax(target_attr, target, link, page, per_page, template_pagination, last_viewed_comment=None):
    maxdepth = None if request.args.get('fulltree') == '1' else 2

    comments_count, paged, comments_tree_list = target.bl.paginate_comments(page, per_page, maxdepth)
    if not comments_tree_list and paged.number != 1:
        abort(404)

    comment_spoiler_threshold = current_app.config['COMMENT_SPOILER_THRESHOLD']
    data = {
        target_attr: target,
        'comments_tree_list': comments_tree_list,
        'last_viewed_comment': last_viewed_comment,
        'num_pages': paged.num_pages,
        'page_current': page,
        'page_obj': paged,
        'comment_spoiler_threshold': comment_spoiler_threshold,
    }

    return jsonify({
        'success': True,
        'link': link,
        'comments_count': comments_count,
        'comments_tree': render_template('includes/comments_tree.html', **data),
        'pagination': render_template(template_pagination, **data),
    })


def ajax_tree(target_attr, comment, target=None, last_viewed_comment=None):
    if not target:
        target = getattr(comment, target_attr)

    # Проще получить все комментарии и потом выбрать оттуда нужные
    comments_tree_list = target.bl.get_comments_tree_list(
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
        target_attr: target,
        'comments_tree_list': tree,
        'last_viewed_comment': last_viewed_comment,
        'comment_spoiler_threshold': comment_spoiler_threshold,
    }

    return jsonify({
        'success': True,
        'tree_for': comment.local_id,
        'comments_tree': render_template('includes/comments_tree.html', **data),
    })
