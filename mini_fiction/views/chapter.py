#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import struct

from flask import Response, Blueprint, request, render_template, abort, url_for, redirect, g, jsonify, current_app
from flask_login import current_user, login_required
from flask_babel import gettext
from pony.orm import db_session

from mini_fiction.bl.migration import enrich_story
from mini_fiction.models import Story, Chapter
from mini_fiction.utils.misc import diff2html, words_count
from mini_fiction.linters import create_chapter_linter
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.chapters import CHAPTER_FORM
from mini_fiction.utils.converter import convert


from .story import get_story

bp = Blueprint('chapter', __name__)


@bp.route('/story/<int:story_id>/chapter/all/', defaults={'chapter_order': None})
@bp.route('/story/<int:story_id>/chapter/<int:chapter_order>/')
@db_session
def view(story_id, chapter_order=None):
    story = get_story(story_id)
    enrich_story(story)

    allow_draft = current_user.is_staff or story.bl.is_contributor(current_user)

    if chapter_order is not None:
        chapter = Chapter.get(story=story_id, order=chapter_order)
        if not chapter:
            abort(404)
        if chapter.draft and not allow_draft:
            abort(404)
        page_title = chapter.autotitle[:80] + ' : ' + story.title
        prev_chapter = chapter.get_prev_chapter(allow_draft)
        next_chapter = chapter.get_next_chapter(allow_draft)
        if current_user.is_authenticated:
            chapter.bl.viewed(current_user)
        data = {
            'story': story,
            'chapter': chapter,
            'prev_chapter': prev_chapter,
            'next_chapter': next_chapter,
            'is_last_chapter': not next_chapter,
            'page_title': page_title,
            'allchapters': False,
            'robots_noindex': not story.published or story.robots_noindex,
        }
    else:
        chapters = list(
            story.bl.select_accessible_chapters(current_user)
            .order_by(Chapter.order, Chapter.id)
        )
        page_title = story.title + ' – все главы'
        if current_user.is_authenticated:
            for c in chapters:
                c.bl.viewed(current_user)
        data = {
            'story': story,
            'chapters': chapters,
            'page_title': page_title,
            'allchapters': True,
            'robots_noindex': not story.published or story.robots_noindex,
        }

    response = Response(render_template('chapter_view.html', **data))
    if (
        current_app.config['CHAPTER_HTML_FRONTEND_CACHE_TIME'] is not None and
        not story.bl.editable_by(current_user)
    ):
        response.cache_control.max_age = current_app.config['CHAPTER_HTML_FRONTEND_CACHE_TIME']
        response.cache_control.private = True
        response.cache_control_exempt = True
    return response


def _gen_preview(*, form, only_selected: bool, formatted: bool):
    title = form.get('title') or gettext('Chapter')
    sel_start = form.get('sel_start') or ''
    sel_end = form.get('sel_end') or ''
    notes_html = Chapter.bl.notes2html(form.get('notes', '')[:4096])

    text = form.get('text', '')[:current_app.config['CHAPTER_MAX_LENGTH']]
    if formatted:
        text = convert(text).text

    if only_selected and sel_start.isdigit() and sel_end.isdigit():
        html = Chapter.bl.text2html(text, start=int(sel_start), end=int(sel_end))
    else:
        html = Chapter.bl.text2html(text)

    return {
        'preview_title': title,
        'preview_html': html,
        'preview_words': words_count(html),
        'notes_preview_html': notes_html,
    }


def _update_publication_status(chapter, user, formdata):
    story = chapter.story
    status = formdata.get('publication_status')

    if status == 'publish_all':
        story.bl.publish_all_chapters(user)

    elif status == 'publish':
        if chapter.draft:
            chapter.bl.publish(user, published=True)

    elif status == 'draft':
        if not chapter.draft:
            chapter.bl.publish(user, published=False)


@bp.route('/story/<int:story_id>/chapter/add/', methods=('GET', 'POST'))
@db_session
@login_required
def add(story_id):
    if request.method == 'POST':
        story = Story.get_for_update(id=story_id)
    else:
        story = Story.get(id=story_id)
    if not story:
        abort(404)
    if not story.bl.editable_by(current_user):
        abort(403)

    preview_data = {'preview_title': None, 'preview_html': None, 'notes_preview_html': None}

    form = {
        'saved': False,
        'not_saved': False,
        'data': {
            'title': request.form.get('title') or '',
            'notes': request.form.get('notes') or '',
            'text': request.form.get('text') or '',
            'publication_status': request.form.get('publication_status') or 'publish',
        },
        'errors': {},
    }

    if request.form.get('act') in ('preview', 'preview_selected'):
        preview_data = _gen_preview(
            form=request.form,
            only_selected=request.form.get('act') == 'preview_selected',
            formatted=current_user.text_source_behaviour
        )

        if request.form.get('ajax') == '1':
            return jsonify(
                success=True,
                html=render_template(
                    'includes/chapter_preview.html',
                    story=story,
                    chapter=None,
                    **preview_data
                )
            )

    elif request.method == 'POST':
        try:
            data = Validator(CHAPTER_FORM).validated(form['data'].copy())
            chapter = Chapter.bl.create(
                story=story,
                editor=current_user,
                data={
                    'title': data['title'],
                    'notes': data['notes'],
                    'text': data['text'],
                },
            )

        except ValidationError as exc:
            form['errors'] = exc.errors
            form['not_saved'] = True

        else:
            _update_publication_status(chapter, current_user, data)

            redir_url = url_for('chapter.edit', pk=chapter.id)

            # Запускаем поиск распространённых ошибок в тексте главы
            linter = create_chapter_linter(chapter.text)
            error_codes = set(linter.lint() if linter else [])

            # Те ошибки, которые пользователь просил не показывать, не показываем
            error_codes = error_codes - set(current_user.bl.get_extra('hidden_chapter_linter_errors') or [])

            if error_codes:
                redir_url += '?lint={}'.format(_encode_linter_codes(error_codes))
            result = redirect(redir_url)
            result.set_cookie('formsaving_clear', 'chapter', max_age=None)
            return result

    ctx = {
        'page_title': 'Добавление новой главы',
        'story': story,
        'chapter': None,
        'form': form,
        'unpublished_chapters_count': Chapter.select(lambda x: x.story == story and x.draft).count(),
        'chapter_max_length': current_app.config['CHAPTER_MAX_LENGTH'],
    }
    ctx.update(preview_data)

    return render_template('chapter_work.html', **ctx)


@bp.route('/chapter/<int:pk>/edit/', methods=('GET', 'POST'))
@db_session
@login_required
def edit(pk):
    if request.method == 'POST':
        chapter = Chapter.get_for_update(id=pk)
    else:
        chapter = Chapter.get(id=pk)
    if not chapter:
        abort(404)

    if not chapter.story.bl.editable_by(current_user):
        abort(403)

    # Параметром ?l=1 просят запустить линтер.
    # Если всё хорошо, то продолжаем дальше.
    # Если плохо, перенаправляем на страницу с описанием ошибок
    lint_ok = None
    if request.method == 'GET' and request.args.get('l') == '1':
        linter = create_chapter_linter(chapter.text)
        error_codes = set(linter.lint() if linter else [])
        # Те ошибки, которые пользователь просил не показывать, показываем,
        # потому что они явно запрошены параметром ?l=1
        if error_codes:
            redir_url = url_for('chapter.edit', pk=chapter.id)
            redir_url += '?lint={}'.format(_encode_linter_codes(error_codes))
            return redirect(redir_url)
        lint_ok = linter is not None

    older_text = None
    chapter_text_diff = []

    preview_data = {'preview_title': None, 'preview_html': None, 'notes_preview_html': None}

    form = {
        'saved': False,
        'not_saved': False,
        'data': {
            'title': request.form.get('title', chapter.title),
            'notes': request.form.get('notes', chapter.notes),
            'text': request.form.get('text', chapter.text),
            'publication_status': request.form.get('publication_status', 'publish'),
            'minor': request.form.get('minor', '') == 'y',
        },
        'errors': {},
    }

    if request.form.get('act') in ('preview', 'preview_selected'):
        preview_data = _gen_preview(
            form=request.form,
            only_selected=request.form.get('act') == 'preview_selected',
            formatted=current_user.text_source_behaviour
        )

        if request.form.get('ajax') == '1':
            return jsonify(
                success=True,
                html=render_template(
                    'includes/chapter_preview.html',
                    story=chapter.story,
                    chapter=chapter,
                    **preview_data
                )
            )

    elif request.method == 'POST':

        try:
            data = Validator(CHAPTER_FORM).validated(form['data'].copy())
        except ValidationError as exc:
            form['errors'] = exc.errors

        if not form['errors'] and request.form.get('older_md5'):
            older_text, chapter_text_diff = chapter.bl.get_diff_from_older_version(request.form['older_md5'])

            if chapter_text_diff:
                form['errors']['text'] = [
                    'Пока вы редактировали главу, её отредактировал кто-то другой. Ниже представлен '
                    'список изменений, которые вы пропустили. Перенесите их в свой текст и сохраните '
                    'главу ещё раз.'
                ]

        if not form['errors']:
            minor = data.pop('minor')
            try:
                chapter.bl.update(
                    editor=current_user,
                    data=data,
                    minor=minor,
                )
            except ValidationError as exc:
                form['errors'] = exc.errors

        if not form['errors']:
            _update_publication_status(chapter, current_user, data)
            form['saved'] = True
            form['data']['text'] = chapter.text
        else:
            form['not_saved'] = True

    # Если мы дошли сюда, значит рисуем форму редактирования главы.
    # В параметре lint могли запросить описание ошибок линтера,
    # запрашиваем их из собственно линтера
    error_codes = []
    linter_error_messages = {}
    linter_allow_hide = ''
    if request.method == 'GET' and request.args.get('lint'):
        error_codes = set(_decode_linter_codes(request.args['lint']))
    if error_codes:
        linter = create_chapter_linter(None)
        linter_error_messages = linter.get_error_messages(error_codes) if linter else []

        # Интересуемся, отображались эти ошибки раньше. Если ни одной новой,
        # разрешаем пользователя попросить больше не показывать
        old_error_codes = set(current_user.bl.get_extra('shown_chapter_linter_errors') or [])
        if not (error_codes - old_error_codes):
            linter_allow_hide = ','.join(str(x) for x in (error_codes | set(current_user.bl.get_extra('hidden_chapter_linter_errors') or [])))
        else:
            current_user.bl.set_extra('shown_chapter_linter_errors', list(error_codes | old_error_codes))

    # Радиокнопки выбора статуса публикации генерируются динамически
    # в зависимости от текущего состояния рассказа
    publication_status = request.form.get('publication_status')
    if publication_status not in ('publish', 'publish_all', 'draft'):
        publication_status = None

    if not publication_status:
        publication_status = 'draft' if chapter.draft else 'publish'

    unpublished_chapters_count = Chapter.select(
        lambda x: x.story == chapter.story and x.draft and x.id != pk
    ).count()

    if unpublished_chapters_count == 0 and publication_status == 'publish_all':
        publication_status = 'publish'

    form['data']['publication_status'] = publication_status

    ctx = {
        'page_title': 'Редактирование главы «%s»' % chapter.autotitle,
        'story': chapter.story,
        'chapter': chapter,
        'form': form,
        'edit': True,
        'chapter_text_diff': chapter_text_diff,
        'diff_html': diff2html(older_text, chapter_text_diff) if chapter_text_diff else None,
        'unpublished_chapters_count': unpublished_chapters_count,
        'chapter_max_length': max(len(chapter.text), current_app.config['CHAPTER_MAX_LENGTH']),
        'linter_error_messages': linter_error_messages,
        'lint_ok': lint_ok,
        'linter_allow_hide': linter_allow_hide,
    }
    ctx.update(preview_data)

    result = current_app.make_response(render_template('chapter_work.html', **ctx))
    if form['saved']:
        result.set_cookie('formsaving_clear', 'chapter', max_age=None)
    return result


@bp.route('/chapter/<int:pk>/hidelinter/', methods=('GET', 'POST'))
@db_session
@login_required
def hidelinter(pk):
    chapter = Chapter.get(id=pk)
    if not chapter:
        abort(404)
    if not chapter.story.bl.editable_by(current_user):
        abort(403)

    if request.method == 'POST':
        error_codes = request.form.get('errors')
        if error_codes:
            try:
                error_codes = [x.strip() for x in error_codes.split(',')]
                error_codes = [int(x) for x in error_codes if x.isdigit() and len(x) < 4]
            except Exception:
                error_codes = []
        else:
            error_codes = []

        error_codes = set(error_codes)
        if len(error_codes) > 1024:
            error_codes = set()
        current_user.bl.set_extra('hidden_chapter_linter_errors', list(error_codes))

    return redirect(url_for('chapter.edit', pk=chapter.id))


@bp.route('/chapter/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@login_required
def delete(pk):
    chapter = Chapter.get(id=pk)
    if not chapter:
        abort(404)
    if not chapter.story.bl.editable_by(current_user):
        abort(403)

    story = chapter.story

    if request.method == 'POST':
        chapter.bl.delete(editor=current_user)
        return redirect(url_for('story.edit_chapters', pk=story.id))

    page_title = 'Подтверждение удаления главы'
    data = {
        'page_title': page_title,
        'story': story,
        'chapter': chapter,
    }

    if g.is_ajax:
        html = render_template('includes/ajax/chapter_ajax_confirm_delete.html', page_title=page_title, story=story, chapter=chapter)
        return jsonify({'page_content': {'modal': html, 'title': page_title}})
    return render_template('chapter_confirm_delete.html', **data)


@bp.route('/chapter/<int:pk>/publish/', methods=('GET', 'POST',))
@db_session
@login_required
def publish(pk):
    chapter = Chapter.get(id=pk)
    if not chapter:
        abort(404)
    if not chapter.story.bl.editable_by(current_user):
        abort(403)

    chapter.bl.publish(current_user, chapter.draft)  # draft == not published
    if g.is_ajax:
        return jsonify({'success': True, 'story_id': chapter.story.id, 'chapter_id': chapter.id, 'published': not chapter.draft})
    return redirect(url_for('story.edit', pk=chapter.story.id))


@bp.route('/story/<int:story_id>/sort/', methods=('POST',))
@db_session
@login_required
def sort(story_id):
    story = Story.get(id=story_id)
    if not story:
        abort(404)
    if not story.bl.editable_by(current_user):
        abort(403)

    if not request.json or not request.json.get('chapters'):
        return jsonify({'success': False, 'error': 'Invalid request'})

    try:
        new_order = [int(x) for x in request.json['chapters']]
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid request'})

    chapters = {c.id: c for c in story.chapters}
    if not new_order or set(chapters) != set(new_order):
        return jsonify({'success': False, 'error': 'Bad request: incorrect list'})

    # Сперва проставляем заведомо несуществующие порядки, чтобы Pony ORM
    # не ругалось на неуникальность ключей
    max_order = max(x.order for x in chapters.values())
    for new_order_id, chapter_id in enumerate(new_order):
        chapters[chapter_id].order = max_order + new_order_id + 1
        chapters[chapter_id].flush()

    # Когда проблемы с неуникальностью решены, проставляем настоящие значения
    for new_order_id, chapter_id in enumerate(new_order):
        chapters[chapter_id].order = new_order_id + 1

    return jsonify({'success': True})


def _encode_linter_codes(error_codes):
    result = 0
    for x in error_codes:
        assert x >= 0 and x <= 31
        result += 1 << x

    result = struct.pack('<I', result).rstrip(b'\x00')
    return base64.urlsafe_b64encode(result).decode('ascii').strip('=')


def _decode_linter_codes(b64):
    b64 = b64.strip().strip('=')
    try:
        b64 += "=" * ((4 - len(b64) % 4) % 4)
        num = base64.urlsafe_b64decode(b64.encode('ascii'))
        num = struct.unpack('<I', num.ljust(4, b'\x00'))[0]
    except Exception:
        return []

    result = []
    for x in range(32):
        if num & (1 << x):
            result.append(x)

    return result
