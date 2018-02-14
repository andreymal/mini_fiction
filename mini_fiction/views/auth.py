#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from flask import Blueprint, current_app, request, render_template, redirect, url_for, flash
from flask_babel import gettext
from flask_login import login_user, logout_user
from pony.orm import db_session

from mini_fiction.models import Author
from mini_fiction.captcha import CaptchaError
from mini_fiction.validation import ValidationError
from mini_fiction.forms.login import LoginForm
from mini_fiction.forms.register import AuthorRegistrationForm, AuthorPasswordResetForm, AuthorNewPasswordForm


bp = Blueprint('auth', __name__)


@bp.route('/login/', methods=('GET', 'POST'))
@db_session
def login():
    page_title = gettext('Authorization')

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = Author.bl.authenticate_by_username(form.data)
            if not login_user(user, remember=True):
                raise ValidationError({'username': [gettext('Cannot login')]})
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            user.last_login = datetime.utcnow()
            user.last_visit = user.last_login
            next_url = request.args.get('next')
            if not next_url or len(next_url) < 2 or next_url[0] != '/' or next_url.startswith('//'):
                next_url = url_for('index.index')
            return redirect(next_url)

    return render_template('registration/login.html', form=form, page_title=page_title)


@bp.route('/register/', methods=('GET', 'POST'))
@db_session
def registration():
    if not current_app.config['REGISTRATION_OPEN']:
        return render_template('registration/registration_closed.html', page_title=gettext('Registration is closed'))

    page_title = gettext('Registration in library')

    captcha = None
    captcha_error = None
    if current_app.captcha:
        captcha = current_app.captcha.generate()

    form = AuthorRegistrationForm()
    if form.validate_on_submit():
        data = dict(form.data)
        if current_app.captcha:
            data = current_app.captcha.copy_fields(data, request.form)
        try:
            Author.bl.register(data)
        except CaptchaError:
            captcha_error = 'Вы не доказали, что вы не робот'
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('auth.registration_complete'))

    return render_template(
        'registration/registration_form.html',
        form=form,
        captcha=captcha,
        captcha_error=captcha_error,
        page_title=page_title,
    )


@bp.route('/register/complete/', methods=('GET',))
@db_session
def registration_complete():
    return render_template('registration/registration_complete.html')


@bp.route('/activate/<activation_key>/', methods=('GET',))
@db_session
def registration_activate(activation_key):
    user = Author.bl.activate(activation_key)
    if user:
        if current_app.config['REGISTRATION_AUTO_LOGIN']:
            login_user(user, remember=True)
        return render_template('registration/activation_complete.html', robots_noindex=True)
    else:
        return render_template('registration/activate.html', robots_noindex=True)


@bp.route('/password/reset/', methods=('GET', 'POST'))
@db_session
def password_reset():
    page_title = 'Восстановление пароля: введите адрес e-mail'

    form = AuthorPasswordResetForm()
    if form.validate_on_submit():
        clean_email = form.email.data.lower().strip()
        users = Author.select(lambda x: x.email.lower() == clean_email)[:2]

        if len(users) == 1:
            users[0].bl.reset_password_by_email()
            return redirect(url_for('auth.password_reset_done'))

        if not users:
            form.set_errors({'email': ['Пользователь с таким e-mail не найден']})
        else:  # len(users) > 1
            form.set_errors({'email': [
                'Как-то получилось, что этот e-mail есть у нескольких пользователей. '
                'Обратитесь к администрации для разбирательств'
            ]})

    return render_template('registration/password_reset_form.html', form=form, page_title=page_title)


@bp.route('/password/reset/done/')
@db_session
def password_reset_done():
    page_title = 'Восстановление пароля: письмо отправлено'
    return render_template('registration/password_reset_done.html', page_title=page_title)


@bp.route('/password/reset/<activation_key>/', methods=('GET', 'POST'))
@db_session
def password_reset_confirm(activation_key):
    page_title = 'Восстановление пароля: новый пароль'
    user = Author.bl.get_by_password_reset_key(activation_key)
    if not user:
        return render_template('registration/password_reset_confirm.html', validlink=False, page_title=page_title)

    form = AuthorNewPasswordForm()
    if form.validate_on_submit():
        if current_app.config['CHECK_PASSWORDS_SECURITY'] and not user.bl.is_password_good(form.new_password1.data):
            flash(gettext('Password is too bad, please change it'))
        else:
            user.bl.set_password(form.new_password1.data)
            if not user.bl.activate_password_reset_key(activation_key):
                raise RuntimeError('activate_password_reset_key returns False')
            return redirect(url_for('auth.password_reset_complete'))
    return render_template('registration/password_reset_confirm.html', validlink=True, form=form, page_title=page_title, robots_noindex=True)


@bp.route('/password/done/')
@db_session
def password_reset_complete():
    page_title = 'Восстановление пароля: пароль восстановлен'
    return render_template('registration/password_reset_complete.html', page_title=page_title)


@bp.route('/changemail/<activation_key>/', methods=('GET',))
@db_session
def new_email_activate(activation_key):
    user = Author.bl.activate_changed_email(activation_key)
    if user:
        if current_app.config['REGISTRATION_AUTO_LOGIN']:
            login_user(user, remember=True)
        return render_template('registration/change_email_complete.html', robots_noindex=True)
    else:
        return render_template('registration/change_email_failed.html', robots_noindex=True)


@bp.route('/logout/', methods=('GET',))
@db_session
def logout():
    logout_user()
    next_url = request.args.get('next')
    if not next_url or len(next_url) < 2 or next_url[0] != '/' or next_url.startswith('//'):
        next_url = url_for('index.index')
    return redirect(next_url)
