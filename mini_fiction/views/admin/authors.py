#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, redirect, url_for
from flask_babel import gettext
from flask_login import login_user, current_user
from pony.orm import db_session

from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.authors import AdminAuthorForm
from mini_fiction.models import Author
from mini_fiction.utils.views import paginate_view

bp = Blueprint('admin_authors', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
def index(page):
    if not current_user.is_superuser:
        abort(403)

    objects = Author.select().order_by(Author.username)

    return paginate_view(
        'admin/authors/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('Authors'),
        objlistname='authors',
        per_page=100,
    )


@bp.route('/<int:pk>/', methods=('GET', 'POST'))
@db_session
def update(pk):
    if not current_user.is_superuser:
        abort(403)

    author = Author.get(id=pk)
    if not author:
        abort(404)

    form = AdminAuthorForm(data={
        'email': author.email,
        'is_active': author.is_active,
        'is_staff': author.is_staff,
        'is_superuser': author.is_superuser,
    })

    saved = False

    if form.validate_on_submit():
        if author.id == current_user.id:
            for true_field in ('is_active', 'is_superuser', 'is_staff'):
                if true_field in form.data and not form.data[true_field]:
                    abort(403)
        try:
            author.bl.update(form.data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    return render_template(
        'admin/authors/update.html',
        page_title=author.username,
        author=author,
        form=form,
        saved=saved,
    )


@bp.route('/<int:pk>/login/', methods=('POST',))
@db_session
def login(pk):
    if not current_user.is_superuser:
        abort(403)

    author = Author.get(id=pk)
    if not author:
        abort(404)
    if not author.is_active:
        abort(403)

    login_user(author)
    return redirect(url_for('author.info'))
