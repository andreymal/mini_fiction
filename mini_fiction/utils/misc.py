#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
import smtplib
from base64 import b64encode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app, g, escape
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


def connectmail(config=None):
    if config is None:
        config = current_app.config

    if config.get('EMAIL_USE_SSL'):
        s = smtplib.SMTP_SSL(
            config['EMAIL_HOST'],
            config['EMAIL_PORT'],
            timeout=10,
            keyfile=config['EMAIL_SSL_KEYFILE'],
            certfile=config['EMAIL_SSL_CERTFILE'],
        )
    else:
        s = smtplib.SMTP(
            config['EMAIL_HOST'],
            config['EMAIL_PORT'],
            timeout=10,
        )

    if not config.get('EMAIL_USE_SSL') and config.get('EMAIL_USE_TLS'):
        s.ehlo()
        s.starttls(keyfile=config['EMAIL_SSL_KEYFILE'], certfile=config['EMAIL_SSL_CERTFILE'])
        s.ehlo()

    if config.get('EMAIL_HOST_USER'):
        s.login(config['EMAIL_HOST_USER'], config['EMAIL_HOST_PASSWORD'])

    return s


def sendmail(to, subject, body, fro=None, config=None):
    if config is None:
        config = current_app.config

    if not config.get('EMAIL_HOST'):
        return False

    if not body:
        return False
    if fro is None:
        fro = config['DEFAULT_FROM_EMAIL']

    if isinstance(subject, str):
        subject = subject.encode("utf-8")
    if isinstance(body, str):
        body = body.encode("utf-8")

    if isinstance(body, bytes):
        msg = MIMEText(body, 'plain', 'utf-8')
    elif len(body) == 1:
        msg = body[0]
    else:
        msg = MIMEMultipart()
        for x in body:
            msg.attach(x)

    msg['From'] = fro
    msg['To'] = to

    subject_b64 = b64encode(subject)
    if isinstance(subject_b64, bytes):
        subject_b64 = subject_b64.decode('ascii')
    subject_b64 = "=?UTF-8?B?" + subject_b64 + "?="
    msg['Subject'] = subject_b64

    try:
        s = connectmail(config)
        s.sendmail(fro, to, msg.as_string().encode('utf-8'))
        s.quit()
    except Exception:
        import traceback
        traceback.print_exc()  # we can't use flask.logger, because it uses sendmail :)
        return False

    return True


def sitename():
    return current_app.config['SITE_NAME'].get(g.locale.language) or current_app.config['SITE_NAME'].get('default', 'Library')


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
