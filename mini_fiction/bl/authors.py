#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import os
import random
import string
from datetime import datetime, timedelta
from base64 import b64decode, b64encode

import scrypt
from flask import current_app, url_for, render_template
from flask_babel import lazy_gettext
from werkzeug.security import safe_str_cmp

try:
    import bcrypt
except ImportError:
    bcrypt = None

from mini_fiction.utils.misc import sendmail
from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import ValidationError, Validator
from mini_fiction.validation.auth import REGISTRATION, LOGIN


__all__ = ['AuthorBL']


class AuthorBL(BaseBL):
    def create(self, data):
        if 'username' not in data or 'password' not in data:
            raise ValidationError({'username': lazy_gettext('Please set username and password')})

        errors = {}
        if self.model.select(lambda x: x.username == data['username']):
            errors['username'] = [lazy_gettext('User already exists')]
        if current_app.config['CHECK_PASSWORDS_SECURITY'] and not self.is_password_good(data['password'], extra=(data['username'],)):
            errors['password'] = [lazy_gettext('Password is too bad, please change it')]
        if data.get('email') and self.model.select(lambda x: x.email == data['email']).exists():
            errors['email'] = [lazy_gettext('Email address is already in use')]
        if errors:
            raise ValidationError(errors)

        user = self._model()(
            username=data['username'],
            email=data.get('email') or '',
            is_active=bool(data.get('is_active', True)),
            is_staff=bool(data.get('is_staff', False)),
            is_superuser=bool(data.get('is_superuser', False)),
        )
        user.flush()  # for user.id
        user.bl.set_password(data['password'])
        return user

    def update(self, data):
        user = self.model
        for field in ('bio', 'jabber', 'skype', 'tabun', 'forum', 'vk', 'email'):
            if field in data:
                setattr(user, field, data[field])
        if 'excluded_categories' in data:
            user.excluded_categories = ','.join(str(x) for x in data['excluded_categories'])
        for field in ('is_staff', 'is_active', 'is_superuser', 'detail_view', 'nsfw'):
            if field in data:
                setattr(user, field, bool(data[field]))

    def register(self, data):
        from mini_fiction.models import RegistrationProfile

        data = Validator(REGISTRATION).validated(data)
        data['is_active'] = False
        user = self.create(data)

        rp = RegistrationProfile(
            user=user,
            activation_key=''.join(random.choice(string.ascii_letters + string.digits) for _ in range(40)),
            activated=False,
        )
        rp.flush()

        sendmail(
            data['email'],
            render_template('registration/activation_email_subject.txt'),
            render_template('registration/activation_email.txt', activation_key=rp.activation_key),
        )

        return user

    def reset_password_by_email(self):
        from mini_fiction.models import PasswordResetProfile

        user = self.model
        if not user.email:
            raise ValueError('User has no email')

        prp = PasswordResetProfile.select(
            lambda x: x.user == user and not x.activated and x.date > datetime.utcnow() - timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS'])
        ).first()
        if prp:
            prp.delete()

        prp = PasswordResetProfile(
            user=user,
            activation_key=''.join(random.choice(string.ascii_letters + string.digits) for _ in range(40)),
            activated=False,
        )
        prp.flush()

        sendmail(
            user.email,
            render_template('registration/password_reset_email_subject.txt'),
            render_template('registration/password_reset_email.txt', activation_key=prp.activation_key, user=user),
        )

        return prp

    def get_by_password_reset_key(self, activation_key):
        from mini_fiction.models import PasswordResetProfile

        prp = PasswordResetProfile.select(
            lambda x: not x.activated and x.activation_key == activation_key
        ).first()
        if not prp:
            # key is activated or not exists
            return
        if prp.date + timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS']) < datetime.utcnow():
            # key is expired
            return
        return prp.user

    def activate_password_reset_key(self, activation_key):
        from mini_fiction.models import PasswordResetProfile

        prp = PasswordResetProfile.select(
            lambda x: not x.activated and x.activation_key == activation_key
        ).first()
        if not prp:
            return False
        prp.activated = True
        return True

    def activate(self, activation_key):
        from mini_fiction.models import RegistrationProfile
        rp = RegistrationProfile.get(activation_key=activation_key)
        if not rp:
            return
        user = rp.user
        if user.is_active and not rp.activated:
            # unreal case
            return
        elif rp.activated and not user.is_active:
            # user is already registered and banned
            return
        elif user.date_joined + timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS']) < datetime.utcnow():
            # key is expired
            return
        rp.activated = True
        user.is_active = True
        return user

    def authenticate(self, password):
        if not password:
            return False

        data = self._model().password
        if not data:
            return False

        if data.startswith('$scrypt$'):
            try:
                b64_salt, Nexp, r, p, keylen, h = data.split('$')[2:]
                Nexp = int(Nexp, 10)
                r = int(r, 10)
                p = int(p, 10)
                keylen = int(keylen, 10)
            except:
                raise ValueError('Invalid hash format')
            return safe_str_cmp(h, self._generate_password_hash(password, b64_salt, Nexp, r, p, keylen))

        elif bcrypt is not None and data.startswith('$bcrypt$'):
            try:
                encoded = data.split('$', 2)[2].encode('utf-8')
                encoded2 = bcrypt.hashpw(password.encode('utf-8'), encoded)
                return safe_str_cmp(encoded, encoded2)
            except:
                raise ValueError('Invalid hash format')

        else:
            raise NotImplementedError('Unknown algorithm')

    def authenticate_by_username(self, data):
        data = Validator(LOGIN).validated(data)
        user = None
        if data['username']:
            user = self._model().select(lambda x: x.username == data['username']).first()
        if not user or not user.bl.authenticate(data['password']):
            raise ValidationError({'username': [lazy_gettext('Please enter a correct username and password. Note that both fields may be case-sensitive.')]})
        if not user.is_active:
            raise ValidationError({'username': [lazy_gettext('Account is disabled')]})
        return user

    def set_password(self, password):
        user = self.model

        if not password:
            user.password = ''
            return

        if current_app.config['PASSWORD_HASHER'] == 'scrypt':
            b64_salt = b64encode(os.urandom(32)).decode('ascii')
            args = {'b64_salt': b64_salt, 'Nexp': 14, 'r': 8, 'p': 1, 'keylen': 64}
            h = self._generate_password_hash(password, **args)
            user.password = '$scrypt${b64_salt}${Nexp}${r}${p}${keylen}${h}'.format(h=h, **args)

        elif bcrypt is not None and current_app.config['PASSWORD_HASHER'] == 'bcrypt':
            salt = bcrypt.gensalt()
            encoded = bcrypt.hashpw(password.encode('utf-8'), salt)
            user.password = '$bcrypt$' + encoded.decode('utf-8', 'ascii')

    def _generate_password_hash(self, password, b64_salt, Nexp=14, r=8, p=1, keylen=64):
        h = scrypt.hash(
            password.encode('utf-8'),
            b64decode(b64_salt),
            2 << Nexp, r, p, keylen
        )
        return b64encode(h).decode('ascii')

    def is_password_good(self, password, extra=()):
        if len(password) < 6:
            return False
        if password in extra:
            return False
        if password in ('password', 'qwer1234'):
            return False
        if password == (password[0] * len(password)):
            return False
        for seq in ('1234567890', 'qwertyuiop', 'q1w2e3r4t5y6u7i8o9p0'):
            v = ''
            for x in seq:
                v += x
                if password == v:
                    return False
        return True

    def get_full_name(self):
        user = self._model()
        full_name = '{} {}'.format(user.first_name, user.last_name)
        return full_name.strip()

    def get_short_name(self):
        return self._model().first_name

    def get_avatar_url(self):
        url = self.get_tabun_avatar_url()
        if url:
            return url

        return url_for('static', filename='i/userpic.jpg')

    def get_small_avatar_url(self):
        url = self.get_tabun_avatar_url()
        if url:
            return url.replace('100x100', '24x24')

        return url_for('static', filename='i/userpic.jpg')

    def get_tabun_avatar_url(self):
        tabun = self._model().tabun
        if not tabun:
            return

        url = None
        try:
            key = 'tabun_avatar:' + tabun
            url = current_app.cache.get(key)
            if current_app.config['LOAD_TABUN_AVATARS'] and not url:
                import urllib.request
                from urllib.parse import urljoin
                import lxml.etree as etree

                profile_url = 'https://tabun.everypony.ru/profile/' + urllib.request.quote(tabun)
                req = urllib.request.Request(profile_url)
                req.add_header('User-Agent', 'Mozilla/5.0; mini_fiction')  # for CloudFlare
                data = urllib.request.urlopen(req).read()
                doc = etree.HTML(data.decode('utf-8'))
                links = doc.xpath('//*[contains(@class, "profile-info-about")]//a[contains(@class, "avatar")]/img/@src')
                if links:
                    url = urljoin(profile_url, links[0])
                current_app.cache.set(key, url, timeout=300 * (1 + random.random()))
        except Exception:
            if current_app.config['DEBUG']:
                import traceback
                traceback.print_exc()

        return url
