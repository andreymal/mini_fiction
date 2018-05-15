#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app, request, g, jsonify, abort, redirect, render_template
from flask_login import current_user
from flask_babel import gettext

from mini_fiction.forms.comment import CommentForm
from mini_fiction.captcha import CaptchaError
from mini_fiction.validation import ValidationError
from mini_fiction.utils.misc import calc_maxdepth
from mini_fiction.validation.utils import safe_string_multiline_coerce


def build_comment_tree_response(comment, target_attr, target):
    html = render_template(
        'includes/comments_tree.html',
        **{
            target_attr: target,
            'comments_tree_list': [[comment, False, 0, 0]]
        }
    )
    return {
        'success': True,
        target_attr: target.id,
        'comment': comment.local_id,
        'global_id': comment.id,
        'deleted': comment.deleted,
        'link': comment.bl.get_paged_link(current_user._get_current_object()),
        'html': html
    }


def build_comment_response(comment, target_attr, target):
    html = render_template('includes/comment_single.html', comment=comment)
    return jsonify({
        'success': True,
        target_attr: target.id,
        'comment': comment.local_id,
        'global_id': comment.id,
        'deleted': comment.deleted,
        'link': comment.bl.get_paged_link(current_user._get_current_object()),
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

    # Проверки доступа (дублируются в Comment.bl.create, но здесь они тоже нужны,
    # чтобы пользователь не получил содержимое parent, когда доступа не должно быть)
    if parent and not parent.bl.access_for_answer_by(user):
        if request.method != 'POST':
            return redirect(parent.bl.get_paged_link(user))
        abort(403)

    reqs = target.bl.access_for_commenting_by(user)
    if not reqs:
        if parent and request.method != 'POST':
            return redirect(parent.bl.get_paged_link(user))
        abort(403)

    extra_ajax = g.is_ajax and request.form.get('extra_ajax') == '1'
    preview_html = None

    form = CommentForm()
    captcha_error = None

    if request.form.get('act') == 'preview':
        preview_html = target.bl.comment2html(request.form.get('text'))

        if request.form.get('ajax') == '1':
            return jsonify(
                success=True,
                html=render_template('includes/comment_preview.html', preview_html=preview_html),
            )

    elif form.validate_on_submit():
        # Обработка POST-запроса
        data = dict(form.data)
        if current_app.captcha:
            data = current_app.captcha.copy_fields(data, request.form)

        # Если родительский комментарий указан через query string, а не форму
        if parent:
            data['parent'] = parent.local_id

        # Проверяем, что точно такого же коммента не отправлялось ранее
        # (тащим coerce из валидатора, так как данные могут меняться после валидации)
        comment = None
        if user.is_authenticated:
            coerced_text = safe_string_multiline_coerce(data['text'].strip())
            comment = target.comments.select(
                lambda c: c.author == user and c.parent == parent and c.text == coerced_text and not c.deleted
            ).first()

        created = not comment

        # Собственно создание
        if not comment:
            try:
                # FIXME: здесь проверяется капча, а надо перед валидацией формы,
                # чтобы не оставалось висячих капч (ох уж эти рефакторинги)
                comment = target.bl.create_comment(user, request.remote_addr, data)
            except CaptchaError:
                captcha_error = 'Вы не доказали, что вы не робот'
            except ValidationError as exc:
                form.set_errors(exc.errors)

        # Если коммент создан (или уже был ранее), то отвечаем успехом
        if comment:
            if extra_ajax:
                # Для AJAX отвечаем просто html-кодом комментария и всякой технической инфой
                result = build_comment_tree_response(comment, target_attr, target)
                result['captcha_html'] = render_template('captcha/captcha.html', captcha=current_app.captcha.generate()) if reqs.get('captcha') else None
                result['created'] = created
                response = jsonify(result)
            else:
                # Иначе редиректим на страницу с комментарием
                response = redirect(comment.bl.get_paged_link(current_user._get_current_object()))

            response.set_cookie('formsaving_clear', 'comment', max_age=None)
            return response

    # При ошибках с AJAX не церемонимся и просто отсылаем строку с ошибками
    # (на фронтенде будет всплывашка в углу)
    if extra_ajax and captcha_error:
        return jsonify({
            'success': False,
            'error': captcha_error,
            'captcha_html': render_template('captcha/captcha.html', captcha=current_app.captcha.generate()),
        })
    elif extra_ajax and (form.errors or form.non_field_errors):
        errors = sum(form.errors.values(), []) + form.non_field_errors
        errors = '; '.join(str(x) for x in errors)
        return jsonify({
            'success': False,
            'error': errors,
            'captcha_html': render_template('captcha/captcha.html', captcha=current_app.captcha.generate()) if reqs.get('captcha') else None,
        })

    # Здесь код рисования полноценной страницы с формой
    data = {
        'page_title': gettext('Add new comment'),
        'form': form,
        target_attr: target,
        'parent_comment': parent,
        'edit': False,
        'preview_html': preview_html,
        'robots_noindex': True,
        'comment_reqs': reqs,
        'captcha_error': captcha_error,
    }

    if g.is_ajax and template_ajax:
        html = render_template(template_ajax, **data)
        return jsonify({'page_content': {'modal': html} if template_ajax_modal else {'content': html}})
    return render_template(template, **data)


def show(target_attr, comment):
    # В эту вьюху направляет ссылка из метода get_permalink
    user = current_user._get_current_object()
    target = getattr(comment, target_attr)

    if not comment.bl.has_comments_access(target, user):
        abort(403)

    return redirect(comment.bl.get_paged_link(current_user._get_current_object()))


def edit(target_attr, comment, template, template_ajax=None, template_ajax_modal=False):
    user = current_user._get_current_object()
    target = getattr(comment, target_attr)

    if not comment.bl.can_update_by(user):
        abort(403)

    extra_ajax = g.is_ajax and request.form.get('extra_ajax') == '1'
    preview_html = None
    form = CommentForm(request.form, data={'text': comment.text})

    if request.form.get('act') == 'preview':
        preview_html = target.bl.comment2html(request.form.get('text'))

        if request.form.get('ajax') == '1':
            return jsonify(
                success=True,
                html=render_template('includes/comment_preview.html', preview_html=preview_html, comment=comment),
            )

    elif form.validate_on_submit():
        try:
            comment.bl.update(user, request.remote_addr, form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            if extra_ajax:
                response = build_comment_response(comment, target_attr, target)
            else:
                response = redirect(comment.bl.get_paged_link(user))
            response.set_cookie('formsaving_clear', 'comment', max_age=None)
            return response

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
        'preview_html': preview_html,
        'comment_reqs': None,
        'robots_noindex': True,
    }

    if g.is_ajax and template_ajax:
        html = render_template(template_ajax, **data)
        return jsonify({'page_content': {'modal': html} if template_ajax_modal else {'content': html}})
    return render_template(template, **data)


def delete(target_attr, comment, template, template_ajax=None, template_ajax_modal=False):
    user = current_user._get_current_object()
    target = getattr(comment, target_attr)

    if not comment.bl.can_delete_by(user):
        abort(403)

    extra_ajax = g.is_ajax and request.form.get('extra_ajax') == '1'
    if request.method == 'POST':
        comment.bl.delete(user)  # из БД не удаляется!
        if extra_ajax:
            return build_comment_response(comment, target_attr, target)
        return redirect(comment.bl.get_paged_link(user))

    data = {
        'page_title': gettext('Confirm delete comment'),
        target_attr: target,
        'comment': comment,
        'comment_delete': True,
        'robots_noindex': True,
    }

    if g.is_ajax and template_ajax:
        html = render_template(template_ajax, **data)
        return jsonify({'page_content': {'modal': html} if template_ajax_modal else {'content': html}})
    return render_template(template, **data)


def restore(target_attr, comment, template, template_ajax=None, template_ajax_modal=False):
    user = current_user._get_current_object()
    target = getattr(comment, target_attr)

    if not comment.bl.can_restore_by(user):
        abort(403)

    extra_ajax = g.is_ajax and request.form.get('extra_ajax') == '1'
    if request.method == 'POST':
        comment.bl.restore(user)
        if extra_ajax:
            return build_comment_response(comment, target_attr, target)
        else:
            return redirect(comment.bl.get_paged_link(user))

    data = {
        'page_title': gettext('Confirm restore comment'),
        target_attr: target,
        'comment': comment,
        'comment_restore': True,
        'robots_noindex': True,
    }

    if g.is_ajax and template_ajax:
        html = render_template(template_ajax, **data)
        return jsonify({'page_content': {'modal': html} if template_ajax_modal else {'content': html}})
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


def ajax(target_attr, target, link, page, per_page, template_pagination, last_viewed_comment=None, extra_data=None):
    if not target.bl.has_comments_access(current_user._get_current_object()):
        abort(403)

    maxdepth = None if request.args.get('fulltree') == '1' else calc_maxdepth(current_user)

    comments_count, paged, comments_tree_list = target.bl.paginate_comments(page, per_page, maxdepth, last_viewed_comment=last_viewed_comment)
    if not comments_tree_list and paged.number != 1:
        abort(404)

    comment_ids = [x[0].id for x in comments_tree_list]
    if current_user.is_authenticated:
        comment_votes_cache = target.bl.select_comment_votes(current_user._get_current_object(), comment_ids)
    else:
        comment_votes_cache = {i: 0 for i in comment_ids}

    data = dict(extra_data or {})
    data.update({
        target_attr: target,
        'comments_tree_list': comments_tree_list,
        'last_viewed_comment': last_viewed_comment,
        'page_obj': paged,
        'comment_votes_cache': comment_votes_cache,
    })

    return jsonify({
        'success': True,
        'link': link,
        'comments_count': comments_count,
        'comments_tree': render_template('includes/comments_tree.html', **data),
        'pagination': render_template(template_pagination, **data),
    })


def ajax_tree(target_attr, comment, target=None, last_viewed_comment=None, extra_data=None):
    if not target:
        target = getattr(comment, target_attr)
    if not target.bl.has_comments_access(current_user._get_current_object()):
        abort(403)

    # Проще получить все комментарии и потом выбрать оттуда нужные
    comments_tree_list = target.bl.get_comments_tree_list(
        maxdepth=None,
        root_id=comment.root_id,
        last_viewed_comment=last_viewed_comment,
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

    comment_ids = [x[0].id for x in tree]
    if current_user.is_authenticated:
        comment_votes_cache = target.bl.select_comment_votes(current_user._get_current_object(), comment_ids)
    else:
        comment_votes_cache = {i: 0 for i in comment_ids}

    data = dict(extra_data or {})
    data.update({
        target_attr: target,
        'comments_tree_list': tree,
        'last_viewed_comment': last_viewed_comment,
        'comment_votes_cache': comment_votes_cache,
    })

    return jsonify({
        'success': True,
        'tree_for': comment.local_id,
        'comments_tree': render_template('includes/comments_tree.html', **data),
    })
