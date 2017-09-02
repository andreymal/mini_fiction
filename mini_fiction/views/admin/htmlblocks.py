#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.htmlblock import HtmlBlockForm
from mini_fiction.models import HtmlBlock

bp = Blueprint('admin_htmlblocks', __name__)


@bp.route('/')
@db_session
@admin_required
def index():
    return render_template(
        'admin/htmlblocks/index.html',
        page_title=gettext('HTML Blocks'),
        htmlblocks=HtmlBlock.select().order_by(HtmlBlock.name)[:],
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = HtmlBlockForm()

    if not current_user.is_superuser:
        del form.is_template

    if form.validate_on_submit():
        try:
            htmlblock = HtmlBlock.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_htmlblocks.update', name=htmlblock.name, lang=htmlblock.lang))

    return render_template(
        'admin/htmlblocks/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<name>/<lang>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(name, lang):
    htmlblock = HtmlBlock.get(name=name, lang=lang)
    if not htmlblock:
        abort(404)

    form = HtmlBlockForm(data={
        'name': htmlblock.name,
        'lang': htmlblock.lang,
        'is_template': htmlblock.is_template,
        'content': htmlblock.content,
    })

    saved = False
    can_edit = True
    if not current_user.is_superuser:
        if htmlblock.is_template:
            can_edit = False
        del form.is_template

    if can_edit and form.validate_on_submit():
        try:
            htmlblock.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/htmlblocks/work.html',
        page_title='{} ({})'.format(htmlblock.name, htmlblock.lang),
        htmlblock=htmlblock,
        form=form,
        can_edit=can_edit,
        edit=True,
        saved=saved,
    )


@bp.route('/<name>/<lang>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(name, lang):
    htmlblock = HtmlBlock.get(name=name, lang=lang)
    if not htmlblock:
        abort(404)

    if not current_user.is_superuser:
        if htmlblock.is_template:
            abort(403)

    if request.method == 'POST':
        try:
            htmlblock.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_htmlblocks.index'))

    return render_template(
        'admin/htmlblocks/delete.html',
        page_title=gettext('Delete'),
        htmlblock=htmlblock,
    )
