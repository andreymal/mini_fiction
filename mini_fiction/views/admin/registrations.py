#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import Blueprint, current_app, render_template, abort, redirect, url_for, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.models import Author, RegistrationProfile
from mini_fiction.utils.misc import Paginator

bp = Blueprint('admin_registrations', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
def index(page):
    if not current_user.is_superuser:
        abort(403)

    objects = RegistrationProfile.select().order_by(RegistrationProfile.id.desc())
    page_obj = Paginator(page, objects.count(), per_page=100)

    return render_template(
        'admin/registrations/index.html',
        registrations=page_obj.slice_or_404(objects),
        page_obj=page_obj,
        page_title=gettext('Registrations'),
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
def update(pk):
    if not current_user.is_superuser:
        abort(403)

    rp = RegistrationProfile.get(id=pk)
    if not rp:
        abort(404)

    if request.method == 'POST' and request.form.get('act') == 'activate':
        user = Author.bl.activate(rp.activation_key)
        user.flush()
        return redirect(url_for('admin_authors.update', pk=user.id))

    too_old = rp.created_at + timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS']) < datetime.utcnow()
    too_old = too_old or Author.exists(email=rp.email)
    too_old = too_old or Author.exists(username=rp.username)

    return render_template(
        'admin/registrations/work.html',
        page_title=rp.username,
        rp=rp,
        too_old=too_old,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
def delete(pk):
    if not current_user.is_superuser:
        abort(403)

    rp = RegistrationProfile.get(id=pk)
    if not rp:
        abort(404)

    if request.method == 'POST':
        rp.delete()
        return redirect(url_for('admin_registrations.index'))

    return render_template(
        'admin/registrations/delete.html',
        page_title=gettext('Delete'),
        rp=rp,
    )
