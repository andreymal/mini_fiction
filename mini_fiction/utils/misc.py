#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import smtplib
from base64 import b64encode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app, g


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


def sendmail(to, subject, body, fro=None, config=None):
    if config is None:
        config = current_app.config

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
        s.sendmail(fro, to, msg.as_string().encode('utf-8'))
        s.quit()
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
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
