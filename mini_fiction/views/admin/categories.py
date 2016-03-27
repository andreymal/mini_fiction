#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.sorting import CategoryForm
from mini_fiction.models import Category
from mini_fiction.utils.views import paginate_view

bp = Blueprint('admin_categories', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = Category.select().order_by(Category.id)

    return paginate_view(
        'admin/categories/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('Categories'),
        objlistname='categories',
        per_page=100,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = CategoryForm()

    if form.validate_on_submit():
        try:
            category = Category.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_categories.update', pk=category.id))

    return render_template(
        'admin/categories/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    category = Category.get(id=pk)
    if not category:
        abort(404)

    form = CategoryForm(data={
        'name': category.name,
        'description': category.description,
        'color': category.color,
    })

    saved = False

    if form.validate_on_submit():
        try:
            category.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/categories/work.html',
        page_title=category.name,
        category=category,
        form=form,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    category = Category.get(id=pk)
    if not category:
        abort(404)

    if request.method == 'POST':
        try:
            category.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_categories.index'))

    return render_template(
        'admin/categories/delete.html',
        page_title=gettext('Delete'),
        category=category,
    )
