#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=exec-used

import sys
import select

import click
from babel import Locale
from flask import current_app, g
from flask_babel import get_babel
from pony.orm import db_session

from mini_fiction.management.manager import cli


@cli.command(help='Runs a Python interactive interpreter.')
@click.option('-c', '--command', 'command', help='Instead of opening an interactive shell, run a command and exit.', required=False)
def shell(command):
    import code
    import mini_fiction
    from mini_fiction import models

    with db_session:
        g.locale = Locale.parse(get_babel().default_locale)

        local = {
            'mini_fiction': mini_fiction,
            'app': current_app,
            'g': g,
            'm': models,
            'system_user': models.Author.get(id=current_app.config['SYSTEM_USER_ID']),
        }

        if command is not None:
            exec(command, local)
            return

        # If stdin is not a tty, just execute the code without opening an interactive shell
        if sys.platform != 'win32' and not sys.stdin.isatty() and select.select([sys.stdin.fileno()], [], [], 0)[0]:
            exec(sys.stdin.read(), local)
            return

        code.interact(local=local)
