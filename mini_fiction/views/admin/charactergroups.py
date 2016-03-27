#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.sorting import CharacterGroupForm
from mini_fiction.models import CharacterGroup
from mini_fiction.utils.views import paginate_view

bp = Blueprint('admin_charactergroups', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = CharacterGroup.select().order_by(CharacterGroup.id)

    return paginate_view(
        'admin/charactergroups/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('Character groups'),
        objlistname='charactergroups',
        per_page=100,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = CharacterGroupForm()

    if form.validate_on_submit():
        try:
            charactergroup = CharacterGroup.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_charactergroups.update', pk=charactergroup.id))

    return render_template(
        'admin/charactergroups/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    charactergroup = CharacterGroup.get(id=pk)
    if not charactergroup:
        abort(404)

    form = CharacterGroupForm(data={
        'name': charactergroup.name,
        'description': charactergroup.description,
    })

    saved = False

    if form.validate_on_submit():
        try:
            charactergroup.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/charactergroups/work.html',
        page_title=charactergroup.name,
        charactergroup=charactergroup,
        form=form,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    charactergroup = CharacterGroup.get(id=pk)
    if not charactergroup:
        abort(404)

    if request.method == 'POST':
        try:
            charactergroup.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_charactergroups.index'))

    return render_template(
        'admin/charactergroups/delete.html',
        page_title=gettext('Delete'),
        charactergroup=charactergroup,
    )
