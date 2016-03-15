#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.notice import NoticeForm
from mini_fiction.models import Notice
from mini_fiction.utils.views import paginate_view

bp = Blueprint('admin_notices', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = Notice.select().order_by(Notice.id.desc())

    return paginate_view(
        'admin/notices/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('Notices'),
        objlistname='notices',
        per_page=100,
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = NoticeForm()

    if not current_user.is_superuser:
        del form.is_template

    if form.validate_on_submit():
        try:
            notice = Notice.bl.create(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_notices.update', pk=notice.id))

    return render_template(
        'admin/notices/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    notice = Notice.get(id=pk)
    if not notice:
        abort(404)

    form = NoticeForm(data={
        'name': notice.name,
        'title': notice.title,
        'is_template': notice.is_template,
        'show': notice.show,
        'content': notice.content,
    })

    saved = False
    can_edit = True
    if not current_user.is_superuser:
        if notice.is_template:
            can_edit = False
        del form.is_template

    if can_edit and form.validate_on_submit():
        try:
            notice.bl.update(current_user._get_current_object(), form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/notices/work.html',
        page_title='{} — {}'.format(notice.name, notice.title or notice.name),
        notice=notice,
        form=form,
        can_edit=can_edit,
        edit=True,
        saved=saved,
    )


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@admin_required
def delete(pk):
    notice = Notice.get(id=pk)
    if not notice:
        abort(404)

    if not current_user.is_superuser:
        if notice.is_template:
            abort(403)

    if request.method == 'POST':
        try:
            notice.bl.delete(current_user._get_current_object())
        except ValidationError:
            abort(403)
        else:
            return redirect(url_for('admin_notices.index'))

    return render_template(
        'admin/notices/delete.html',
        page_title=gettext('Delete'),
        notice=notice,
    )
