import re
import sys
import json
import hmac
import math
import time
from datetime import timedelta
from html import escape
from urllib.request import Request, urlopen
from urllib.parse import quote, urljoin
from typing import AnyStr, List, Optional

import pytz
from werkzeug.urls import url_parse
from babel import Locale
from flask import current_app, g, render_template, abort, url_for, request, has_request_context
from flask_babel import get_babel, pgettext, ngettext

from mini_fiction.utils import diff as utils_diff


soft_urlquote_unsafe_chars = ''.join(
    [chr(x) for x in range(32)] +
    [' :?#[]@!$&\'()*+,;="<>\u007f\u00a0\u00ff\ufffe\ufeff\uffff']
)


class Paginator(object):
    def __init__(self, number=1, total=0, per_page=50, endpoint=None, view_args=None, page_arg_name='page'):
        self.number = number
        self.total = total
        self.per_page = per_page
        self.page_arg_name = page_arg_name

        self.num_pages = max(1, math.ceil(total / self.per_page))
        if self.number == -1:
            self.number = self.num_pages
        self.offset = (self.number - 1) * per_page

        if endpoint:
            self.endpoint = endpoint
        elif has_request_context():
            self.endpoint = request.endpoint
        else:
            self.endpoint = None

        if view_args is not None:
            self.view_args = dict(view_args)
        elif has_request_context():
            self.view_args = dict(request.view_args or {})
        else:
            self.view_args = None

    def slice(self, objlist):
        min_idx = max(0, self.offset)
        max_idx = max(0, self.offset + self.per_page)
        if max_idx - min_idx < 1:
            return []
        return list(objlist[min_idx:max_idx])

    def slice_or_404(self, objlist):
        result = self.slice(objlist)
        if not result and self.number != 1:
            abort(404)
        return result

    def can_generate_url(self):
        return self.endpoint is not None and self.view_args is not None

    def url_for_page(self, number=None):
        if not self.can_generate_url():
            raise ValueError('URLs are unavailable for this paginator')

        if number is None:
            number = self.number

        view_args = dict(self.view_args)
        view_args[self.page_arg_name] = number
        return url_for(self.endpoint, **view_args)

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

    def iter_pages(self, begin_pages=2, end_pages=2, center_pages=1, current_pages=5):
        begin_pages = max(1, int(begin_pages))
        end_pages = max(1, int(end_pages))
        center_pages = max(1, int(center_pages))
        current_pages = max(1, int(current_pages))

        if self.num_pages <= (begin_pages + end_pages):
            for page in range(1, self.num_pages + 1):
                yield page
            return

        # first pages
        for page in range(1, 1 + begin_pages):
            yield page
        last_page = begin_pages

        # first center
        center1 = (self.number - begin_pages) // 2 + begin_pages
        for page in range(center1 - center_pages // 2, center1 + center_pages // 2 + 1):
            if page > last_page and page <= self.num_pages:
                last_page = page
                yield page

        # current page
        for page in range(self.number - current_pages // 2, self.number + current_pages // 2 + 1):
            if page > last_page and page <= self.num_pages:
                last_page = page
                yield page

        # second center
        end_begin = self.num_pages - end_pages + 1
        center2 = (end_begin - last_page) // 2 + last_page
        for page in range(center2 - center_pages // 2, center2 + center_pages // 2 + 1):
            if page > last_page and page <= self.num_pages:
                last_page = page
                yield page

        # last pages
        for page in range(end_begin, self.num_pages + 1):
            if page > last_page and page <= self.num_pages:
                last_page = page
                yield page


class IndexPaginator(Paginator):
    # Особый случай пагинации для главной страницы
    def __init__(self, *args, **kwargs):
        kwargs['endpoint'] = 'stream.stories'
        kwargs['view_args'] = {}
        super().__init__(*args, **kwargs)

    def url_for_page(self, number=None):
        if number is None:
            number = self.number
        if number == 1:
            return url_for('index.index')
        return super().url_for_page(number)


def sitename():
    return current_app.config['SITE_NAME'].get(g.locale.language) or current_app.config['SITE_NAME'].get('default', 'Library')


def copyright():
    return current_app.config['COPYRIGHT'].get(g.locale.language) or current_app.config['COPYRIGHT'].get('default', 'Copyright')


def emailsitename():
    if current_app.config['EMAIL_SITE_NAME'] is None:
        return sitename()
    return current_app.config['EMAIL_SITE_NAME'].get(g.locale.language) or current_app.config['EMAIL_SITE_NAME'].get('default', 'Library')


def indextitle():
    return current_app.config['SITE_INDEX_TITLE'].get(g.locale.language) or current_app.config['SITE_INDEX_TITLE'].get('default', '')


def sitedescription():
    return current_app.config['SITE_DESCRIPTION'].get(g.locale.language) or current_app.config['SITE_DESCRIPTION'].get('default', '')


def call_after_request(f, *args, **kwargs) -> None:
    # FIXME: не будет лишней опция отмены вызова при ошибке 500
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append((f, args, kwargs))


def calc_maxdepth(user=None):
    if user and user.is_authenticated and user.comments_maxdepth is not None:
        maxdepth = user.comments_maxdepth - 1
    else:
        maxdepth = current_app.config['COMMENTS_TREE_MAXDEPTH'] - 1
    if maxdepth < 0:
        maxdepth = None
    return maxdepth


def calc_comment_threshold(user):
    if user.is_authenticated and user.comment_spoiler_threshold is not None:
        return user.comment_spoiler_threshold
    return current_app.config['COMMENT_SPOILER_THRESHOLD']


def get_editlog_extra_info(log_item, prepare_chapter_diff=False, show_newlines=False):
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
            log_extra_item['diff_html'] = diff2html(chapter_text, json.loads(log_item.chapter_text_diff), show_newlines=show_newlines)

    return log_extra_item


def diff2html(s, diff, show_newlines=False):
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

        else:
            fancy_data = data
            if show_newlines:
                fancy_data = fancy_data.replace('\n', '⏎\n')

            if act == '+':
                result.append('<ins>')
                result.append(escape(fancy_data))
                result.append('</ins>')

            elif act == '-':
                result.append('<del>')
                result.append(escape(fancy_data))
                result.append('</del>')
                offset += len(data)

    return ''.join(result)


def render_nonrequest_template(*args, **kwargs):
    '''Обёртка над flask.request_template, просто добавляет некоторые нужные
    переменные в ``flask.g``.

    Если запускается в контексте текущего запроса, то патчит url_adapter,
    чтобы отцепиться от запроса.
    '''
    if not hasattr(g, 'locale'):
        g.locale = Locale.parse(get_babel().default_locale)
    if not hasattr(g, 'timezone'):
        g.timezone = pytz.timezone(get_babel().default_timezone)
    if not hasattr(g, 'is_ajax'):
        g.is_ajax = False
    if not hasattr(g, 'current_user'):
        from mini_fiction.models import ANON
        g.current_user = ANON

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


def striptags(s: str) -> str:
    # Простая удалялка тегов по регуляркам; не используйте как защиту от XSS

    # Добавляем разделительные пробелы тем тегам, которые разделяют слова
    s = re.sub(r'(</?(br|hr|footnote|p|blockquote|img|ul|ol|li|pre)[^>]*?>)', r' \1', s, flags=re.I)
    # Для таких span прописан display: block
    s = re.sub(r'(<span+[^>]{,127} +align=[^>]{,127}>)', r' \1', s, flags=re.I)
    # Разделители добавлены, теперь теги можно удалить
    s = re.sub(r'<!--.*?-->', '', s)
    s = re.sub(r'<[^ <>][^<>]{,1500}?>', '', s)  # 1500 - защита от одиноко стоящих знаков больше/меньше
    return s


def words_split(
    s: str,
    html: bool = True,
    strip_punctuation: bool = False,
    strip_entities: bool = False,
) -> List[str]:
    '''По-умному разделяет строку на слова.'''

    s = str(s)

    if html:
        # Удаляем HTML-теги по умному
        s = striptags(s)
        # HTML-сущности тоже не считаем за слова
        if strip_entities:
            s = re.sub(r'&#?[A-Za-z0-9]{1,16};?', '', s)
        else:
            # Если сущности удалять не просят, заменяем самые популярные на оригинальные символы
            for a, b in [('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'), ('&amp;', '&amp;'), ('&shy;', '\u00ad')]:
                s = s.replace(a, b)

    # Знаки препинания за слова не считаются
    if strip_punctuation:
        s = re.sub(r'[\-\/]+', '', s)
        s = re.sub(r'[.,?!@:;_—…–$%*&<>"«»()]+', ' ', s)
        s = s.replace('\u00ad', '')  # мягкий перенос

    words = s.split()
    return words


def words_count(s: str, html: bool = True) -> int:
    '''По-умному считает число слов в строке.'''
    return len(words_split(s, html=html, strip_punctuation=True, strip_entities=True))


def normalize_text_for_search_index(s: str, html: bool = True) -> str:
    return ' '.join(words_split(s, html=html, strip_entities=False))


def normalize_text_for_search_query(s: str, query_mode: str = "extended") -> str:
    from mini_fiction.apis.amsphinxql import SphinxConnection

    result = s.replace('\u00ad', '')

    if query_mode == "extended":
        return result

    if query_mode == "exact":
        # Выпиливаем спецсимволы за ненадобностью, они лишь ошибки синтаксиса генерят
        toreplace = [
            '\\', '(', ')', '|', '-', '!', '@', '~', '"', '&', '/', '^', '$', '=', '<',
        ]
        for c in toreplace:
            result = result.replace(c, ' ')

        # Костыль: sphinx настроен на минимальную длину 2 символа (по умолчанию),
        # и если есть предлог в предложении, то точное совпадение не ищется.
        # Поэтому предварительно выпиливаем предлоги регуляркой
        min_word_len = current_app.config['SPHINX_INDEX_OPTIONS']['min_word_len']
        result = re.sub(r"\s*\b[A-Za-zА-Яа-яЁё]{%d}\b\s*" % (min_word_len - 1), ' ', result)

        result = SphinxConnection.escape_match(result).strip()
        return '="{}"'.format(result) if result else ''

    # mode "none"
    return SphinxConnection.escape_match(result)


def htmlcrop(text, length, end='...', spaces=' \t\r\n\xa0', max_overflow=300, strip=True):
    '''Безопасная обрезалка текста, которая не разрежет посреди HTML-тега
    (но валидацию кода не проводит и корректный результат не обещает).
    А ещё вырезает HTML-комменты и умеет обрезать слова по пробелам.

    :param str text: что обрезаем
    :param int length: длина, под которую обрезаем (будет подогнана, если
      место обрезки окажется внутри HTML-тега)
    :param str end: строка, которая добавится к обрезанному результату
    :param str spaces: что считать пробелами; если пусто, будет резать
      по буквам, а не по словам
    :param int max_overflow: неотрицательное число означает, насколько можно
      вылезать за указанный length; если тег вылезет за length+overflow, то он
      не будет оставлен, а обрежется. Нуль означает выкидывание тега всегда,
      отрицательное число означает оставление тега в покое. По умолчанию
      значение 300 — должно хватить любым нормальным ссылкам на картинки
    :param bool strip: выкидывать ли пробельные символы в начале и конце
      строки; выкинутые не будут учитываться в длине
    :rtype: str
    '''

    # Вырезаем все комменты, они нам мешаются
    text = re.sub(r'<!--.*?-->', '', text)
    # Удаляем ничего не значащие пробельные символы
    if strip:
        text = text.strip()

    # Если кроме этого другой работы не осталось, то всё
    if not text:
        return ''
    if length < 1:
        return end
    elif length >= len(text):
        return text

    # Ищем начало HTML-тега перед местом обрезки
    f1 = text.rfind('<', 0, length)
    # Ищем конец HTML-тега
    f2 = -1
    if f1 >= 0:
        f2 = text.find('>', f1)

    final_length = length

    # Если конец тега после места обрезки, значит попали внутрь тега
    if f2 >= length:
        final_length = f2 + 1
        # Если тег слишком длинный, то выкидываем его
        if max_overflow >= 0 and (max_overflow == 0 or final_length > length + max_overflow):
            final_length = f1

    elif spaces and length < len(text) and text[length] not in spaces:
        # Если не попали, то обрезаем просто по слову
        f3 = max(text.rfind(x, 0, length) for x in spaces)
        if f3 > 0:
            final_length = f3


    if final_length >= len(text):
        return text
    return text[:final_length] + end


def ping_sitemap(url):
    for ping_url_tmpl in current_app.config.get('SITEMAP_PING_URLS') or []:
        ping_url = ping_url_tmpl.format(url=quote(url))

        req = Request(ping_url)
        req.add_header('Connection', 'close')
        req.add_header('User-Agent', current_app.user_agent)

        try:
            urlopen(req, timeout=20).read()
        except Exception as exc:
            current_app.logger.warning('Cannot ping {!r}: {}'.format(ping_url, exc))


def timedelta_format(tm):
    if isinstance(tm, timedelta):
        tm = tm.total_seconds()

    tm = int(tm)
    minus = False
    if tm < 0:
        minus = True
        tm = -tm

    s = '{:02d}s'.format(tm % 60)
    if tm >= 60:
        s = '{:02d}m'.format((tm // 60) % 60) + s
    if tm >= 3600:
        s = '{}h'.format(tm // 3600) + s

    if minus:
        s = '-' + s
    return s


def normalize_tag(s, whitelist=None, delimeters=None):
    from mini_fiction.validation.utils import safe_string_coerce

    if not s:
        return None

    if whitelist is None:
        whitelist = current_app.config['NORMALIZED_TAGS_WHITELIST']
    if delimeters is None:
        delimeters = current_app.config['NORMALIZED_TAGS_DELIMETERS']
    s = ''.join((
        x if x in whitelist else ('_' if x in delimeters else '')
        for x in safe_string_coerce(s.lower()).strip()
    ))
    while '__' in s:
        s = s.replace('__', '_')
    return s.strip('_')[:32] or None


def smart_split(s, delimeter=','):
    """Допиленный split. Делит строку по разделителю, удаляя пробельные
    символы в начале и конце разделённых строк. Пустые строки удаляет; если
    исходная строка пуста или состоит только из пробельных символов,
    возвращает пустой список. На None тоже возвращает пустой список.
    """

    if not s:
        return []
    result = [x.strip() for x in s.split(delimeter)]
    return [x for x in result if x]


def sanitize_filename(s, strip=False):
    """Удаляет небезопасные символы из имени файла (в том числе слэши).
    """

    from mini_fiction.validation.utils import safe_string_coerce

    s = safe_string_coerce(s)
    if strip:
        s = s.strip()

    for c in '"':
        s = s.replace(c, '')
    for c in '\\/:*?<>|+%@':
        s = s.replace(c, '_')
    if strip:
        while s.startswith('_') or s.endswith('_'):
            s = s.strip('_').strip()
    return s or '_'


def soft_urlquote(s, chars=None):
    """«Добрый» вариант urllib.request.quote, который экранирует только
    заведомо небезопасные для ссылок символы вроде пробела и технических.
    Слэш по умолчанию не экранирует (можно экранировать пути). Удобно
    для получения ссылок с русскими буквами.
    """

    if chars is None:
        chars = soft_urlquote_unsafe_chars
    s = s.replace('%', '%25')
    for c in chars:
        s = s.replace(c, '%{:02X}'.format(ord(c)))
    return s


def check_own_url(url: Optional[str]) -> Optional[str]:
    """Проверяет, что URL принадлежит нашему сайту и на него безопасно
    редиректить. «Нашим» считается хост, прописанный в SERVER_NAME.
    Если наш, то возвращается нормализованный абсолютный URL; если не наш,
    то None.
    """
    if not url:
        return None

    base_scheme = current_app.config["PREFERRED_URL_SCHEME"]
    base_host = current_app.config["SERVER_NAME"]
    base_url = f"{base_scheme}://{base_host}/"

    url_abs = urljoin(base_url, url)
    url_info = url_parse(url_abs)

    if url_info.scheme in ("http", "https") and url_info.netloc == base_host:
        return url_abs
    return None


def safe_str_cmp(a: AnyStr, b: AnyStr) -> bool:
    return hmac.compare_digest(
        a.encode("utf-8") if isinstance(a, str) else a,
        b.encode("utf-8") if isinstance(b, str) else b,
    )


def make_absolute_url(url: str) -> str:
    """Превращает относительную ссылку в абсолютную, основываясь на настройках
    SERVER_NAME и PREFERRED_URL_SCHEME."""
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        scheme = current_app.config["PREFERRED_URL_SCHEME"]
        host = current_app.config["SERVER_NAME"]
        return f"{scheme}://{host}{url}"
    return url


def call_after_request_callbacks() -> None:
    for f, args, kwargs in getattr(g, "after_request_callbacks", ()):
        f(*args, **kwargs)
