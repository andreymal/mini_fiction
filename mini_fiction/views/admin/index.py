#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import Blueprint, render_template, url_for, current_app
from flask_babel import gettext
from pony.orm import db_session

from mini_fiction import models
from mini_fiction.utils.views import admin_required

bp = Blueprint('admin_index', __name__)


@bp.route('/')
@db_session
@admin_required
def index():
    log = models.AdminLog.bl.get_list()
    for x in log['items']:
        x['admin_url'] = get_adminlog_object_url(x['type_str'], x['object_id'])

    ctx = {
        'page_title': gettext('Administration'),
        'log': log,
    }

    last_24_hours = datetime.utcnow() - timedelta(days=1)

    # Статистика по жалобам
    ctx['abuse_unresolved_count'] = models.AbuseReport.select(lambda x: not x.ignored and x.resolved_at is None).count()
    abuse_last = models.AbuseReport.select().order_by(models.AbuseReport.created_at.desc()).first()
    ctx['abuse_last'] = abuse_last.created_at if abuse_last else None

    # Статистика по оценкам
    ctx['vote_last_count'] = models.Vote.select(lambda x: x.revoked_at is None and x.updated >= last_24_hours).count()
    ctx['vote_last'] = models.Vote.select().order_by(models.Vote.updated.desc()).first()

    # Статистика по пользователям
    ctx['author_last_count'] = models.Author.select(lambda x: x.activated_at >= last_24_hours).count()
    ctx['author_last'] = models.Author.select().order_by(models.Author.id.desc()).first()

    # Статистика по регистрациям
    account_registration_mindate = datetime.utcnow() - timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS'])
    ctx['registrationprofile_count'] = models.RegistrationProfile.select(lambda x: x.created_at >= account_registration_mindate).count()
    ctx['registrationprofile_last'] = models.RegistrationProfile.select().order_by(models.RegistrationProfile.id.desc()).first()

    return render_template('admin/index.html', **ctx)


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
