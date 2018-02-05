#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, render_template, abort, redirect, url_for, request
from flask_babel import gettext
from flask_login import login_user, current_user
from pony.orm import db_session

from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.authors import AdminAuthorForm, AdminEditPasswordForm
from mini_fiction.models import Author
from mini_fiction.utils.misc import Paginator
from mini_fiction.utils.views import admin_sort

bp = Blueprint('admin_authors', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
def index(page):
    if not current_user.is_superuser:
        abort(403)

    objects = Author.select().order_by(Author.username)

    args = {
        'page': page,
        'sorting': request.args.get('sorting') or 'id',
    }

    if request.args.get('username'):
        args['username'] = request.args['username']
        objects = objects.filter(lambda x: args['username'].lower() in x.username.lower())
    if request.args.get('email'):
        args['email'] = request.args['email']
        objects = objects.filter(lambda x: args['email'].lower() in x.email.lower())

    objects = admin_sort(args['sorting'], objects, {
        'username': Author.username,
        'date_joined': (Author.date_joined, Author.id),
        'last_visit': (Author.last_visit, Author.id),
        'is_active': (Author.is_active, Author.id),
        'id': Author.id,
    })

    page_obj = Paginator(page, objects.count(), per_page=100)

    return render_template(
        'admin/authors/index.html',
        authors=page_obj.slice_or_404(objects),
        page_obj=page_obj,
        page_title=gettext('Authors'),
        endpoint=request.endpoint,
        args=args,
    )


@bp.route('/<pk>/', methods=('GET', 'POST'))
@db_session
def update(pk):
    if not current_user.is_superuser:
        abort(403)

    try:
        pk = int(pk)
    except Exception:
        abort(404)

    author = Author.get(id=pk)
    if not author:
        abort(404)

    form = AdminAuthorForm(data={
        'email': author.email,
        'is_active': author.is_active,
        'is_staff': author.is_staff,
        'is_superuser': author.is_superuser,
        'premoderation_mode': author.premoderation_mode,
    })

    password_edit_form = AdminEditPasswordForm()

    saved = False

    if request.form.get('act') == 'save':
        if form.validate_on_submit():
            if author.id == current_user.id:
                for true_field in ('is_active', 'is_superuser', 'is_staff'):
                    if true_field in form.data and not form.data[true_field]:
                        abort(403)
            try:
                author.bl.update(form.data, modified_by_user=current_user._get_current_object(), fill_admin_log=True)
            except ValidationError as exc:
                form.set_errors(exc.errors)
            else:
                saved = True

    elif request.form.get('act') == 'change_password':
        if password_edit_form.validate_on_submit():
            author.bl.set_password(password_edit_form.data['new_password_1'])
            saved = True

    return render_template(
        'admin/authors/update.html',
        page_title=author.username,
        author=author,
        is_system_user=author.id == current_app.config['SYSTEM_USER_ID'],
        form=form,
        password_edit_form=password_edit_form,
        saved=saved,
    )


@bp.route('/<pk>/login/', methods=('POST',))
@db_session
def login(pk):
    if not current_user.is_superuser:
        abort(403)

    try:
        pk = int(pk)
    except Exception:
        abort(404)

    author = Author.get(id=pk)
    if not author:
        abort(404)
    if not author.is_active:
        abort(403)

    login_user(author)
    return redirect(url_for('author.info'))
