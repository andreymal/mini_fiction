#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app

from mini_fiction.utils.mail import sendmail
from mini_fiction.utils.misc import render_nonrequest_template


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
