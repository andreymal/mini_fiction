#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import smtplib
from email.header import Header
from email.utils import formataddr
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app


def smtp_connect(config=None):
    if config is None:
        config = current_app.config

    if config.get('EMAIL_USE_SSL'):
        s = smtplib.SMTP_SSL(
            config['EMAIL_HOST'],
            config['EMAIL_PORT'],
            timeout=config['EMAIL_TIMEOUT'],
            keyfile=config['EMAIL_SSL_KEYFILE'],
            certfile=config['EMAIL_SSL_CERTFILE'],
        )
    else:
        s = smtplib.SMTP(
            config['EMAIL_HOST'],
            config['EMAIL_PORT'],
            timeout=config['EMAIL_TIMEOUT'],
        )

    if not config.get('EMAIL_USE_SSL') and config.get('EMAIL_USE_TLS'):
        s.ehlo()
        s.starttls(keyfile=config['EMAIL_SSL_KEYFILE'], certfile=config['EMAIL_SSL_CERTFILE'])
        s.ehlo()

    if config.get('EMAIL_HOST_USER'):
        s.login(config['EMAIL_HOST_USER'], config['EMAIL_HOST_PASSWORD'])

    return s


def build_email_body(body):
    prep_body = []

    for item in body:
        if isinstance(item, str):
            item = item.encode('utf-8')

        if isinstance(item, bytes):
            # text/plain
            prep_body.append(MIMEText(item, 'plain', 'utf-8'))
            continue

        if isinstance(item, dict):
            # multipart/alternative
            item = item.copy()
            alt = []

            if 'plain' in item:
                # text/plain
                p = item.pop('plain')
                if isinstance(p, str):
                    p = p.encode('utf-8')
                alt.append(MIMEText(p, 'plain', 'utf-8'))

            if 'html' in item:
                # text/html
                p = item.pop('html')
                if isinstance(p, str):
                    p = p.encode('utf-8')
                alt.append(MIMEText(p, 'html', 'utf-8'))

            if item:
                raise NotImplementedError('non-text emails are not implemeneted')

            # build alternative
            if len(alt) == 1:
                m = alt[0]
            else:
                m = MIMEMultipart('alternative')
                for x in alt:
                    m.attach(x)

            prep_body.append(m)
            continue

        if isinstance(item, MIMEBase):
            prep_body.append(item)
            continue

        raise ValueError('Incorrect body type: {}'.format(type(item)))

    if len(prep_body) == 1:
        return prep_body[0]

    m = MIMEMultipart('mixed')
    for x in prep_body:
        m.attach(x)
    return m


def sendmail(to, subject, body, fro=None, headers=None, config=None, conn=None):
    '''Отправляет письмо по электронной почте на указанные адреса.

    В качестве отправителя ``fro`` может быть указана как просто почта, так и
    список из двух элементов: имени отправителя и почты.

    Тело письма ``body`` может быть очень произвольным:

    - str или bytes: отправляется простое text/plain письмо;
    - словарь: если элементов больше одного, то будет multipart/alternative,
      если элемент один, то только он и будет:
      - plain: простое text/plain письмо;
      - html: HTML-письмо;
    - что-то наследующееся от MIMEBase;
    - всё перечисленное в списке: будет отправлен multipart/mixed со всем
      перечисленным.

    :param to: получатели (может быть переопределено настройкой
      EMAIL_REDIRECT_TO)
    :type to: str или list
    :param str subject: тема письма
    :param body: содержимое письма
    :param fro: отправитель (по умолчанию DEFAULT_FROM_EMAIL)
    :type fro: str, list, tuple
    :param dict headers: дополнительные заголовки (значения — строки
      или списки)
    :param dict config: словарь с настройками почты
    :rtype: bool
    '''

    if config is None:
        config = current_app.config

    if fro is None:
        fro = config['DEFAULT_FROM_EMAIL']

    if not isinstance(fro, str):
        if isinstance(fro, (tuple, list)) and len(fro) == 2:
            # make From: =?utf-8?q?Name?= <e@mail>
            fro = formataddr((Header(fro[0], 'utf-8').encode(), fro[1]))
        else:
            raise ValueError('Non-string from address must be [name, email] list')

    if not config.get('EMAIL_HOST') or not body:
        return False

    if config.get('EMAIL_REDIRECT_TO') is not None:
        if not config.get('EMAIL_DONT_EDIT_SUBJECT_ON_REDIRECT'):
            subject = '[To: {!r}] {}'.format(to, subject or '').rstrip()
        to = config['EMAIL_REDIRECT_TO']

    if not isinstance(to, (tuple, list, set)):
        to = [to]

    if not isinstance(body, (list, tuple)):
        body = [body]

    msg = build_email_body(body)

    msg['From'] = fro
    msg['Subject'] = Header(subject, 'utf-8').encode()

    prep_headers = {'X-Postmaster-Msgtype': config['EMAIL_MSGTYPES']['default']}
    if headers:
        prep_headers.update(headers)

    for header, value in prep_headers.items():
        if not isinstance(value, (list, tuple, set)):
            value = [value]
        for x in value:
            msg[header] = x

    try:
        close_conn = False
        if not conn:
            conn = smtp_connect(config)
            close_conn = True

        for x in to:
            del msg['To']
            msg['To'] = x
            conn.sendmail(fro, x, msg.as_string().encode('utf-8'))

        if close_conn:
            conn.quit()
    except Exception:
        import traceback
        traceback.print_exc()  # we can't use flask.logger, because it uses sendmail :)
        return False

    return True
