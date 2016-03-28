#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.sorting import ClassifierForm
from mini_fiction.models import Classifier
from mini_fiction.utils.views import paginate_view

bp = Blueprint('admin_classifications', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = Classifier.select().order_by(Classifier.id)

    return paginate_view(
        'admin/classifications/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('Classifications'),
        objlistname='classifications',
        per_page=100,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = ClassifierForm()

    if form.validate_on_submit():
        try:
            classifier = Classifier.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_classifications.update', pk=classifier.id))

    return render_template(
        'admin/classifications/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    classifier = Classifier.get(id=pk)
    if not classifier:
        abort(404)

    form = ClassifierForm(data={
        'name': classifier.name,
        'description': classifier.description,
    })

    saved = False

    if form.validate_on_submit():
        try:
            classifier.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/classifications/work.html',
        page_title=classifier.name,
        classifier=classifier,
        form=form,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    classifier = Classifier.get(id=pk)
    if not classifier:
        abort(404)

    if request.method == 'POST':
        try:
            classifier.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_classifications.index'))

    return render_template(
        'admin/classifications/delete.html',
        page_title=gettext('Delete'),
        classifier=classifier,
    )
