#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.misc import Paginator
from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.tag_categories import TagCategoryForm
from mini_fiction.models import TagCategory

bp = Blueprint('admin_tag_categories', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = TagCategory.select().order_by(TagCategory.id)

    page_obj = Paginator(page, objects.count(), per_page=100)
    objects = page_obj.slice_or_404(objects)

    return render_template(
        'admin/tag_categories/index.html',
        page_title=gettext('Tag categories'),
        tag_categories=objects,
        page_obj=page_obj,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = TagCategoryForm()

    if form.validate_on_submit():
        try:
            tag_category = TagCategory.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_tag_categories.update', pk=tag_category.id))

    return render_template(
        'admin/tag_categories/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    tag_category = TagCategory.get(id=pk)
    if not tag_category:
        abort(404)

    form = TagCategoryForm(data={
        'name': tag_category.name,
        'color': tag_category.color,
        'description': tag_category.description,
    })

    saved = False

    if form.validate_on_submit():
        try:
            tag_category.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/tag_categories/work.html',
        page_title=tag_category.name,
        tag_category=tag_category,
        form=form,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    tag_category = TagCategory.get(id=pk)
    if not tag_category:
        abort(404)

    if request.method == 'POST':
        try:
            tag_category.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_tag_categories.index'))

    return render_template(
        'admin/tag_categories/delete.html',
        page_title=gettext('Delete'),
        tag_category=tag_category,
    )
