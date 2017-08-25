#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

from pony.orm import db_session
from flask import current_app, send_from_directory, render_template, abort, url_for


def localstatic(filename):
    return send_from_directory(os.path.abspath(current_app.config['LOCALSTATIC_ROOT']), filename)


def media(filename):
    return send_from_directory(os.path.abspath(current_app.config['MEDIA_ROOT']), filename)


@db_session
def dump():
    if not current_app.config.get('ZIP_DUMP_PATH'):
        abort(404)

    path = os.path.join(current_app.config['MEDIA_ROOT'], current_app.config['ZIP_DUMP_PATH'])
    if not os.path.isfile(path):
        abort(404)

    mtime = datetime.utcfromtimestamp(os.stat(path).st_mtime)

    return render_template(
        'dump.html',
        page_title='Дамп настроек сайта',
        dump_url=url_for('media', filename=current_app.config['ZIP_DUMP_PATH']),
        dump_size_kib=os.path.getsize(path) / 1024.0,
        mtime=mtime,
    )
