#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.staticpage import StaticPageForm
from mini_fiction.models import StaticPage
from mini_fiction.utils.views import paginate_view

bp = Blueprint('admin_staticpages', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = StaticPage.select().order_by(StaticPage.name)

    return paginate_view(
        'admin/staticpages/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('Static pages'),
        objlistname='staticpages',
        per_page=100,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = StaticPageForm()

    if not current_user.is_superuser:
        del form.is_template

    if form.validate_on_submit():
        try:
            staticpage = StaticPage.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_staticpages.update', pk=staticpage.id))

    return render_template(
        'admin/staticpages/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    staticpage = StaticPage.get(id=pk)
    if not staticpage:
        abort(404)

    form = StaticPageForm(data={
        'name': staticpage.name,
        'lang': staticpage.lang,
        'title': staticpage.title,
        'is_template': staticpage.is_template,
        'is_full_page': staticpage.is_full_page,
        'content': staticpage.content,
    })

    saved = False
    can_edit = True
    if not current_user.is_superuser:
        if staticpage.is_template:
            can_edit = False
        del form.is_template

    if can_edit and form.validate_on_submit():
        try:
            staticpage.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/staticpages/work.html',
        page_title='{} — {} ({})'.format(staticpage.name, staticpage.title or staticpage.name, staticpage.lang),
        staticpage=staticpage,
        form=form,
        can_edit=can_edit,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    staticpage = StaticPage.get(id=pk)
    if not staticpage:
        abort(404)

    if not current_user.is_superuser:
        if staticpage.is_template:
            abort(403)

    if request.method == 'POST':
        try:
            staticpage.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_staticpages.index'))

    return render_template(
        'admin/staticpages/delete.html',
        page_title=gettext('Delete'),
        staticpage=staticpage,
    )
