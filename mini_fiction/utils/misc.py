#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import math
import time

from flask import current_app, g, escape, render_template, abort
from flask_babel import pgettext, ngettext

from mini_fiction.utils import diff as utils_diff


class Paginator(object):
    def __init__(self, number=1, total=0, per_page=50, begin_pages=3, end_pages=3, current_pages=5):
        self.number = number
        self.total = total
        self.per_page = per_page

        self.begin_pages = max(1, begin_pages)
        self.end_pages = max(1, end_pages)
        self.current_pages = max(1, current_pages)

        self.num_pages = max(1, math.ceil(total / self.per_page))
        if self.number == -1:
            self.number = self.num_pages
        self.offset = (self.number - 1) * per_page

    def slice(self, objlist):
        if self.offset < 0:
            return []
        return objlist[self.offset:self.offset + self.per_page]

    def slice_or_404(self, objlist):
        result = self.slice(objlist)
        if not result and self.number != 1:
            abort(404)
        return result

    def has_next(self):
        return self.number < self.num_pages

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.number > 1 or self.number < self.num_pages

    def previous_page_number(self):
        return self.number - 1 if self.number > 1 else None

    def next_page_number(self):
        return self.number + 1 if self.number < self.num_pages else None

    def iter_pages(self):
        if self.num_pages <= (self.begin_pages + self.end_pages):
            for i in range(1, self.num_pages + 1):
                yield i
            return

        # first pages
        page = 1
        for page in range(1, 1 + self.begin_pages):
            yield page

        # current page
        cur_begin = self.number - self.current_pages // 2
        end_begin = self.num_pages - self.end_pages + 1
        for page in range(max(page + 1, cur_begin), min(end_begin, cur_begin + self.current_pages)):
            yield page

        # last pages
        for page in range(end_begin, self.num_pages + 1):
            yield page


def sitename():
    return current_app.config['SITE_NAME'].get(g.locale.language) or current_app.config['SITE_NAME'].get('default', 'Library')


def indextitle():
    return current_app.config['SITE_INDEX_TITLE'].get(g.locale.language) or current_app.config['SITE_INDEX_TITLE'].get('default', '')


def sitedescription():
    return current_app.config['SITE_DESCRIPTION'].get(g.locale.language) or current_app.config['SITE_DESCRIPTION'].get('default', '')


def call_after_request(f, *args, **kwargs):
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append((f, args, kwargs))
    return f


def calc_maxdepth(user):
    if user.is_authenticated and user.comments_maxdepth is not None:
        maxdepth = user.comments_maxdepth - 1
    else:
        maxdepth = current_app.config['COMMENTS_TREE_MAXDEPTH'] - 1
    if maxdepth < 0:
        maxdepth = None
    return maxdepth


def calc_comment_threshold(user):
    if user.is_authenticated and user.comment_spoiler_threshold is not None:
        return user.comment_spoiler_threshold
    else:
        return current_app.config['COMMENT_SPOILER_THRESHOLD']


def get_editlog_extra_info(log_item, prepare_chapter_diff=False):
    if not log_item.chapter_action:
        # Изменение рассказа
        log_extra_item = {'mode': 'story', 'list_items': False, 'label': pgettext('story_edit_log', 'edited story')}
        edited_data = log_item.data

        if len(edited_data) == 1:
            if 'draft' in edited_data and edited_data['draft'][1] is False:
                log_extra_item['label'] = pgettext('story_edit_log', 'published story')
            elif 'draft' in edited_data and edited_data['draft'][1] is True:
                log_extra_item['label'] = pgettext('story_edit_log', 'sent to drafts story')
            elif 'approved' in edited_data and edited_data['approved'][1] is True:
                log_extra_item['label'] = pgettext('story_edit_log', 'approved story')
            elif 'approved' in edited_data and edited_data['approved'][1] is False:
                log_extra_item['label'] = pgettext('story_edit_log', 'unapproved story')
            else:
                log_extra_item['list_items'] = True
        else:
            log_extra_item['list_items'] = True

    else:
        # Изменение главы
        log_extra_item = {
            'mode': 'chapter',
            'list_items': False,
            'label': pgettext('story_edit_log', 'edited chapter'),
            'diff_html_available': False,
            'diff_html': None,
        }
        edited_data = log_item.data

        if log_item.chapter_action == 'add':
            log_extra_item['label'] = pgettext('story_edit_log', 'added chapter')
        elif log_item.chapter_action == 'delete':
            log_extra_item['label'] = pgettext('story_edit_log', 'deleted chapter')
        elif len(edited_data) == 1 and 'draft' in edited_data:
            if edited_data['draft'][1]:
                log_extra_item['label'] = pgettext('story_edit_log', 'sent to drafts chapter')
            else:
                log_extra_item['label'] = pgettext('story_edit_log', 'published chapter')
        elif edited_data:
            log_extra_item['list_items'] = True

        if log_item.chapter and log_item.chapter_text_diff:
            log_extra_item['diff_html_available'] = True

        if prepare_chapter_diff and log_extra_item['diff_html_available']:
            # Для отображения диффа пользователю его надо разжать, получив старый текст
            chapter_text = log_item.chapter.bl.get_version(log_item=log_item)
            chapter_text = utils_diff.revert_diff(chapter_text, json.loads(log_item.chapter_text_diff))

            # Теперь у нас есть старый текст, и можно отрисовать данный дифф к нему
            log_extra_item['diff_html'] = diff2html(chapter_text, json.loads(log_item.chapter_text_diff))

    return log_extra_item


def diff2html(s, diff):
    result = []
    ctx = max(0, current_app.config['DIFF_CONTEXT_SIZE'])
    offset = 0
    for i, item in enumerate(diff):
        act, data = item

        if act == '=':
            data = s[offset:offset + data]
            if len(data) < ctx * 3:
                result.append(escape(data))
            else:
                if ctx == 0:
                    l, mid, r = '', data, ''
                elif i == 0:
                    l, mid, r = '', data[:-ctx], data[-ctx:]
                elif i == len(diff) - 1:
                    l, mid, r = data[:ctx], data[ctx:], ''
                else:
                    l, mid, r = data[:ctx], data[ctx:-ctx], data[-ctx:]

                f = l.rfind(' ', 0, len(l) - 2)
                if f >= 0 and f > ctx - 30:
                    mid = l[f:] + mid
                    l = l[:f]
                f = r.find(' ', len(r) + 2)
                if f < ctx + 30:
                    mid = mid + r[:f + 1]
                    r = r[f + 1:]

                result.append(escape(l))
                result.append('<div class="editlog-expand-btn-wrap"><a href="#" class="editlog-expand-btn">')
                result.append(ngettext('Show %(num)s unchanged symbol', 'Show %(num)s unchanged symbols', len(mid)))
                result.append('</a></div><span class="editlog-unchanged" style="display: none;">')
                result.append(escape(mid))
                result.append('</span>')
                result.append(escape(r))
            offset += len(data)

        elif act == '+':
            result.append('<ins>')
            result.append(escape(data))
            result.append('</ins>')

        elif act == '-':
            result.append('<del>')
            result.append(escape(data))
            result.append('</del>')
            offset += len(data)

    return ''.join(result)


def render_nonrequest_template(*args, **kwargs):
    '''Обёртка над flask.request_template, просто добавляет некоторые нужные
    переменные в ``flask.g``.
    '''
    if not hasattr(g, 'locale'):
        g.locale = current_app.extensions['babel'].default_locale
    if not hasattr(g, 'is_ajax'):
        g.is_ajax = False
    if not hasattr(g, 'current_user'):
        from mini_fiction.models import AnonymousUser
        g.current_user = AnonymousUser()

    # Некоторые сволочи типа Flask-Script запускают код в контексте фейкового
    # запроса, что меняет поведение url_for, а это нам нафиг не надо.
    # Костыляем контекст, возвращая нужное поведение. Ну а ещё это позволяет
    # рисовать шаблоны для почты в контексте настоящего запроса, тоже полезно
    from flask.globals import _request_ctx_stack, _app_ctx_stack
    appctx = _app_ctx_stack.top
    reqctx = _request_ctx_stack.top
    old_adapter = None
    if reqctx and reqctx.url_adapter:
        old_adapter = reqctx.url_adapter
        reqctx.url_adapter = appctx.url_adapter

    try:
        return render_template(*args, **kwargs)
    finally:
        if old_adapter is not None:
            reqctx.url_adapter = old_adapter


def progress_drawer(
    target, w=30, progress_chars=None, lb=None, rb=None, humanize=False,
    show_count=False, fps=25.0, file=sys.stdout
):
    '''Подготавливает всё для рисования полоски прогресса и возвращает
    сопрограмму, в которую следует передавать текущий прогресс.

    Суть такова:

    1. Вызываем функцию, передавая первым параметром target значение, которое
       будет считаться за 100%. Полученную сопрограмму сохраняем и запускаем
       вызовом ``send(None)``.

    2. При каждом обновлении передаём текущий прогресс через ``send(N)``.
       Функция посчитает проценты относительно target и отрисует полоску
       загрузки (если ранее уже рисовалась, то отрисует поверх старой).
       Чаще чем ``fps`` кадров в секунду не перерисовывает.

    3. После завершения передаём прогресс, равный target (что даст 100%),
       а потом передаём None. Сопрограмма завершит работу и выкинет
       StopIteration.

    :param int target: число, которое будет считаться за 100%
    :param int w: длина полоски в символах (без учёта границы и процентов)
    :param str progress_chars: символы для рисования прогресса (первый —
       пустая часть, последний — полная часть, между ними — промежуточные
       состояния)
    :param str lb: левая граница полоски
    :param str rb: правая граница полоски
    :param bool humanize: при True выводит текущее значение в кибибайтах
       (делённое на 1024), при False как есть
    :param bool show_count: при True печатает также target
    :param float fps: максимально допустимая частота кадров. Работает так:
       если между двумя send частота получается больше чем fps, то один кадр
       не рисуется и пропускается, однако 100% никогда не пропускается
    :param file file: куда печатать всё это дело, по умолчанию sys.stdout
    :rtype: types.GeneratorType
    '''

    # Выбираем, какими символами будем рисовать полоску
    encoding = file.encoding if hasattr(file, 'encoding') else sys.stdout.encoding
    good_charset = (encoding or '').lower() in ('utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'utf-32')
    if not progress_chars:
        if good_charset:
            progress_chars = ' ▏▎▍▌▋▊▉█'
        else:
            progress_chars = ' -#'
    if lb is None:
        lb = '▕' if good_charset else ' ['
    if rb is None:
        rb = '▏' if good_charset else '] '

    min_period = 1 / fps  # для 25 fps это 0.04

    current = 0
    old_current = None
    old_line = None

    tm = 0
    lastlen = 0

    while current is not None:
        # Умная математика, сколько каких блоков выводить
        part = (current * 1.0 / target) if target > 0 else 1.0
        if part < 0.0:
            part = 0.0
        elif part > 1.0:
            part = 1.0

        full_blocks = int(part * w)
        empty_blocks = w - full_blocks - 1
        part_block_position = (part * w) - full_blocks
        part_block_num = int(part_block_position * (len(progress_chars) - 1))

        # Готовим строку с числовой информацией о прогрессе, чтобы вывести после полоски
        if show_count:
            if humanize:
                cnt_string = '({}K/{}K) '.format(int(current / 1024.0), int(target / 1024.0))
            else:
                cnt_string = '({}/{}) '.format(current, target)
        else:
            if humanize:
                cnt_string = '({}K) '.format(int(current / 1024.0))
            else:
                cnt_string = '({}) '.format(current)

        # Обновляем полоску:
        # - только когда значение новое
        # - не чаще 25 кадров в секунду, но только если текущее значение
        #   не совпадает с 100% (чтобы последний кадр гарантированно
        #   отрисовался)
        if current != old_current and (current == target or time.time() - tm >= min_period):
            old_current = current

            # Собираем всю полоску
            line = lb
            line += progress_chars[-1] * full_blocks
            if full_blocks != w:
                line += progress_chars[part_block_num]
            line += progress_chars[0] * empty_blocks
            line += rb
            line += '{:.1f}% '.format(part * 100).rjust(7)
            line += cnt_string

            # Печатаем её (только если полоска вообще изменилась)
            if line != old_line:
                old_line = line
                lastlen = fprint_substring(line, lastlen, file=file)

                # Запоминаем время печати для ограничения кадров в секунду
                tm = time.time()

        current = yield


def fprint_substring(s, l=0, file=sys.stdout):
    '''Печатает строку, затирая последние l символов.'''

    if l > 0:
        print('\b' * l, end='', file=file)
    print(s, end='', file=file)
    if len(s) < l:
        print(' ' * (l - len(s)), end='', file=file)
        print('\b' * (l - len(s)), end='', file=file)
    if hasattr(file, 'flush'):
        file.flush()
    return len(s)
