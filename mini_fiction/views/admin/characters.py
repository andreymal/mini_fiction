#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.sorting import CharacterForm
from mini_fiction.models import Character, CharacterGroup
from mini_fiction.utils.views import paginate_view

bp = Blueprint('admin_characters', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = Character.select().order_by(Character.id)

    return paginate_view(
        'admin/characters/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('Characters'),
        objlistname='characters',
        per_page=100,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = CharacterForm()

    if form.validate_on_submit():
        try:
            character = Character.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_characters.update', pk=character.id))

    return render_template(
        'admin/characters/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    character = Character.get(id=pk)
    if not character:
        abort(404)

    form = CharacterForm(data={
        'name': character.name,
        'description': character.description,
        'group': character.group.id if character.group else CharacterGroup.select().first().id,
    })

    saved = False

    if form.validate_on_submit():
        try:
            character.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/characters/work.html',
        page_title=character.name,
        character=character,
        form=form,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    character = Character.get(id=pk)
    if not character:
        abort(404)

    if request.method == 'POST':
        try:
            character.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_characters.index'))

    return render_template(
        'admin/characters/delete.html',
        page_title=gettext('Delete'),
        character=character,
    )
