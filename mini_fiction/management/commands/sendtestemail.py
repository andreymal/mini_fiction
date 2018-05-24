#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from pony.orm import db_session
from flask import current_app

from mini_fiction.utils.mail import sendmail
from mini_fiction.utils.misc import render_nonrequest_template

from mini_fiction.management.manager import cli


@cli.command(short_help='Sends a testing email.', help='Sends a test email to the email addresses specified as arguments.')
@click.option('-e', '--eager', 'eager', help='Don\'t use Celery for delayed sending.', is_flag=True)
@click.argument('recipients', nargs=-1, required=True)
@db_session
def sendtestemail(recipients, eager):
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
