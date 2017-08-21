#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.logopic import LogopicForm
from mini_fiction.models import Logopic
from mini_fiction.utils.misc import Paginator

bp = Blueprint('admin_logopics', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = Logopic.select().order_by(Logopic.id)

    page_obj = Paginator(page, objects.count(), per_page=100)
    objects = page_obj.slice_or_404(objects)

    return render_template(
        'admin/logopics/index.html',
        page_title=gettext('Header pictures'),
        logopics=objects,
        page_obj=page_obj,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = LogopicForm()

    if form.validate_on_submit():
        try:
            logopic = Logopic.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_logopics.update', pk=logopic.id))

    return render_template(
        'admin/logopics/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    logopic = Logopic.get(id=pk)
    if not logopic:
        abort(404)

    form = LogopicForm(data={
        'visible': logopic.visible,
        'description': logopic.description,
        'original_link': logopic.original_link,
        'original_link_label': logopic.original_link_label,
    })

    saved = False

    if form.validate_on_submit():
        try:
            logopic.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/logopics/work.html',
        page_title=gettext('Header picture'),
        logopic=logopic,
        form=form,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    logopic = Logopic.get(id=pk)
    if not logopic:
        abort(404)

    if request.method == 'POST':
        try:
            logopic.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_logopics.index'))

    return render_template(
        'admin/logopics/delete.html',
        page_title=gettext('Delete header picture'),
        logopic=logopic,
    )
