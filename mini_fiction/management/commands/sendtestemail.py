#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import current_app, render_template

from mini_fiction.utils.mail import sendmail


def sendtestemail(recipients, eager=False):
    with current_app.test_request_context():
        current_app.preprocess_request()  # fills g.locale

        kwargs = {
            'to': recipients,
            'subject': render_template('email/test_subject.txt'),
            'body': {
                'plain': render_template('email/test.txt'),
                'html': render_template('email/test.html'),
            },
        }

    if eager:
        sendmail(**kwargs)
    else:
        current_app.tasks['sendmail'].delay(**kwargs)
