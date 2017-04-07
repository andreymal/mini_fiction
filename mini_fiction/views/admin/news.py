#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.newsitem import NewsItemForm
from mini_fiction.models import NewsItem
from mini_fiction.utils.views import paginate_view

bp = Blueprint('admin_news', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = NewsItem.select().order_by(NewsItem.id.desc())

    return paginate_view(
        'admin/news/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('News'),
        objlistname='news',
        per_page=100,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = NewsItemForm()

    if not current_user.is_superuser:
        del form.is_template

    if form.validate_on_submit():
        try:
            newsitem = NewsItem.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_news.update', pk=newsitem.id))

    return render_template(
        'admin/news/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    newsitem = NewsItem.get(id=pk)
    if not newsitem:
        abort(404)

    form = NewsItemForm(data={
        'name': newsitem.name,
        'title': newsitem.title,
        'is_template': newsitem.is_template,
        'show': newsitem.show,
        'content': newsitem.content,
    })

    saved = False
    can_edit = True
    if not current_user.is_superuser:
        if newsitem.is_template:
            can_edit = False
        del form.is_template

    if can_edit and form.validate_on_submit():
        try:
            newsitem.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/news/work.html',
        page_title='{} — {}'.format(newsitem.name, newsitem.title or newsitem.name),
        newsitem=newsitem,
        form=form,
        can_edit=can_edit,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    newsitem = NewsItem.get(id=pk)
    if not newsitem:
        abort(404)

    if not current_user.is_superuser:
        if newsitem.is_template:
            abort(403)

    if request.method == 'POST':
        try:
            newsitem.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_news.index'))

    return render_template(
        'admin/news/delete.html',
        page_title=gettext('Delete'),
        newsitem=newsitem,
    )
