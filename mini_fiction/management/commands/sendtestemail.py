#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import db_session
from flask import current_app

from mini_fiction.utils.mail import sendmail
from mini_fiction.utils.misc import render_nonrequest_template

from mini_fiction.management.manager import manager


@manager.option('-e', '--eager', dest='eager', help='Don\'t use Celery for delayed sending', action='store_true')
@manager.option('recipients', metavar='recipients', nargs='+', default=(), help='Recipient addresses')
@db_session
def sendtestemail(recipients, eager=False):
    kwargs = {
        'to': recipients,
        'subject': render_nonrequest_template('email/test_subject.txt'),
        'body': {
            'plain': render_nonrequest_template('email/test.txt'),
            'html': render_nonrequest_template('email/test.html'),
        },
    }

    if eager:
        sendmail(**kwargs)
    else:
        current_app.tasks['sendmail'].delay(**kwargs)
