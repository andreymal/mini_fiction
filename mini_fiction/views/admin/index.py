#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import Blueprint, render_template, url_for, current_app
from flask_babel import gettext
from pony.orm import db_session, desc

from mini_fiction import models
from mini_fiction.logic.adminlog import get_list
from mini_fiction.utils.views import admin_required

bp = Blueprint('admin_index', __name__)


@bp.route('/')
@db_session
@admin_required
def index():
    ctx = {
        'page_title': gettext('Administration'),
        'log': get_list(),
    }

    last_24_hours = datetime.utcnow() - timedelta(days=1)

    # Статистика по жалобам
    ctx['abuse_unresolved_count'] = models.AbuseReport.select(lambda x: not x.ignored and x.resolved_at is None).count()
    abuse_last = models.AbuseReport.select().sort_by(desc(models.AbuseReport.created_at)).first()
    ctx['abuse_last'] = abuse_last.created_at if abuse_last else None

    # Статистика по оценкам
    ctx['vote_last_count'] = models.Vote.select(lambda x: x.revoked_at is None and x.updated >= last_24_hours).count()
    ctx['vote_last'] = models.Vote.select().sort_by(desc(models.Vote.updated)).first()

    # Статистика по пользователям
    ctx['author_last_count'] = models.Author.select(lambda x: x.activated_at >= last_24_hours).count()
    ctx['author_last'] = models.Author.select().sort_by(desc(models.Author.id)).first()

    # Статистика по регистрациям
    account_registration_mindate = datetime.utcnow() - timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS'])
    ctx['registrationprofile_count'] = models.RegistrationProfile.select(
        lambda x: x.activated_by_user is None and x.created_at >= account_registration_mindate
    ).count()
    ctx['registrationprofile_last'] = models.RegistrationProfile.select().sort_by(desc(models.RegistrationProfile.id)).first()

    return render_template('admin/index.html', **ctx)
