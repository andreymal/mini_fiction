import os
from datetime import datetime

from flask import current_app, send_from_directory, render_template, abort, url_for
from pony.orm import db_session


def localstatic(filename):
    return send_from_directory(os.path.abspath(current_app.config['LOCALSTATIC_ROOT']), filename)


def media(filename):
    return send_from_directory(current_app.config['MEDIA_ROOT'].as_posix(), filename)


@db_session
def dump():
    if not current_app.config.get('ZIP_DUMP_PATH'):
        abort(404)

    path = current_app.config['MEDIA_ROOT'] / current_app.config['ZIP_DUMP_PATH']
    if not path.exists():
        abort(404)

    mtime = datetime.utcfromtimestamp(os.stat(path).st_mtime)

    return render_template(
        'dump.html',
        page_title='Дамп настроек сайта',
        dump_url=url_for('media', filename=current_app.config['ZIP_DUMP_PATH']),
        dump_size_kib=os.path.getsize(path) / 1024.0,
        mtime=mtime,
    )
