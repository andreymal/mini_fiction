import json
import os
from dataclasses import asdict
from datetime import datetime

from flask import current_app, send_from_directory, render_template, abort, url_for, Response, request
from flask_login import login_required
from pony.orm import db_session

from mini_fiction.utils.converter import convert


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


@login_required
def converter() -> Response:
    raw_text = request.data.decode()
    result = convert(raw_text)
    response = current_app.response_class(json.dumps(asdict(result), ensure_ascii=False), mimetype='application/json')
    return response
