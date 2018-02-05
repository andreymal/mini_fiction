#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, url_for
from flask_babel import gettext
from pony.orm import db_session

from mini_fiction.models import AdminLog
from mini_fiction.utils.views import admin_required

bp = Blueprint('admin_index', __name__)


@bp.route('/')
@db_session
@admin_required
def index():
    log = AdminLog.bl.get_list()
    for x in log['items']:
        x['admin_url'] = get_adminlog_object_url(x['type_str'], x['object_id'])
        print(x['type_str'], '-', x['admin_url'])

    return render_template('admin/index.html', page_title=gettext('Administration'), log=log)


def get_adminlog_object_url(typ, pk):
    if typ == 'abusereport':
        return url_for('admin_abuse_reports.show', abuse_id=pk)
    if typ == 'author':
        return url_for('admin_authors.update', pk=pk)
    if typ == 'category':
        return url_for('admin_categories.update', pk=pk)
    if typ == 'character':
        return url_for('admin_characters.update', pk=pk)
    if typ == 'charactergroup':
        return url_for('admin_charactergroups.update', pk=pk)
    if typ == 'classifier':
        return url_for('admin_classifications.update', pk=pk)
    if typ == 'htmlblock':
        return url_for('admin_htmlblocks.update', name=pk[0], lang=pk[1])
    if typ == 'logopic':
        return url_for('admin_logopics.update', pk=pk)
    if typ == 'newsitem':
        return url_for('admin_news.update', pk=pk)
    if typ == 'staticpage':
        return url_for('admin_staticpages.update', name=pk[0], lang=pk[1])
    return None
