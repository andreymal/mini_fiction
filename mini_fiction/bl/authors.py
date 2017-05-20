#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import os
import time
import random
import string
from io import BytesIO
from datetime import datetime, timedelta

from flask import current_app, url_for, render_template
from flask_babel import lazy_gettext

from mini_fiction import hashers
from mini_fiction.utils.misc import call_after_request as later
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
        if data.get('email') and self.is_email_busy(data['email']):
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
        for field in ('bio', 'email', 'premoderation_mode'):
            if field in data:
                setattr(user, field, data[field])
        if 'excluded_categories' in data:
            user.excluded_categories = ','.join(str(x) for x in data['excluded_categories'])
        for field in ('is_staff', 'is_active', 'is_superuser', 'detail_view', 'nsfw'):
            if field in data:
                setattr(user, field, bool(data[field]))
        if 'comments_maxdepth' in data:
            if user.comments_maxdepth is None and data['comments_maxdepth'] == current_app.config['COMMENTS_TREE_MAXDEPTH']:
                pass  # Если бралось значение из настроек проекта, то его и оставляем
            else:
                user.comments_maxdepth = int(data['comments_maxdepth'])
        if 'comment_spoiler_threshold' in data:
            if user.comment_spoiler_threshold is None and data['comment_spoiler_threshold'] == current_app.config['COMMENT_SPOILER_THRESHOLD']:
                pass  # Если бралось значение из настроек проекта, то его и оставляем
            else:
                user.comment_spoiler_threshold = int(data['comment_spoiler_threshold'])

        if 'contacts' in data:
            contacts = [x for x in data['contacts'] if x.get('name') and x.get('value')]
            lenc = len(contacts)

            schemas = {}
            for x in current_app.config['CONTACTS']:
                schema = dict(x.get('schema') or {})
                schema['type'] = 'string'
                schema['maxlength'] = 255
                schemas[x['name']] = schema

            errors = {}
            for i, x in enumerate(contacts):
                if x.get('name') not in schemas:
                    errors[i] = {'name': [lazy_gettext('Invalid contact type')]}
                    continue
                schema = dict(schemas[x['name']])
                v = Validator({'value': schema})
                v.validate({'value': x['value']})
                if v.errors:
                    errors[i] = v.errors

            if errors:
                raise ValidationError({'contacts': errors})

            from mini_fiction.models import Contact

            old_contacts = Contact.select(lambda x: x.author == user).order_by(Contact.id)[:]
            while len(old_contacts) > lenc:
                old_contacts.pop().delete()

            for oldc, newc in zip(old_contacts, contacts):
                if oldc.name != newc['name']:
                    oldc.name = newc['name']
                if oldc.value != newc['value']:
                    oldc.value = newc['value']

            i = len(old_contacts)
            while i < lenc:
                old_contacts.append(Contact(
                    author=user,
                    name=contacts[i]['name'],
                    value=contacts[i]['value'],
                ))
                i = len(old_contacts)

        if data.get('delete_avatar'):
            self.delete_avatar()
        elif current_app.config['AVATARS_UPLOADING'] and data.get('avatar'):
            from PIL import Image

            image_data = data['avatar'].stream.read(256 * 1024 + 1)
            if len(image_data) > 256 * 1024:
                raise ValidationError({'avatar': [lazy_gettext('Too big avatar; must be {value} KiB or smaller').format(value=256)]})

            try:
                image = Image.open(BytesIO(image_data))
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                raise ValidationError({'avatar': [lazy_gettext('Cannot read avatar')]})
            else:
                with image:
                    self.validate_and_set_avatar(image, image_data)

    def delete_avatar(self):
        user = self.model

        root = os.path.join(current_app.config['MEDIA_ROOT'])

        if user.avatar_small:
            path = os.path.join(root, user.avatar_small)
            if os.path.isfile(path):
                os.remove(path)
            user.avatar_small = ''

        if user.avatar_medium:
            path = os.path.join(root, user.avatar_medium)
            if os.path.isfile(path):
                os.remove(path)
            user.avatar_medium = ''

        if user.avatar_large:
            path = os.path.join(root, user.avatar_large)
            if os.path.isfile(path):
                os.remove(path)
            user.avatar_large = ''

    def validate_and_set_avatar(self, image, image_data=None):
        if not current_app.config['AVATARS_UPLOADING']:
            raise ValidationError({'avatar': ['Avatar uploading is disabled']})

        from PIL import Image

        user = self.model

        # Валидация размера
        errors = []
        if image.size[0] < 16 or image.size[1] < 16:
            errors.append(lazy_gettext('Too small avatar; must be {w}x{h} or bigger').format(w=16, h=16))
        if image.size[0] > 512 or image.size[1] > 512:
            errors.append(lazy_gettext('Too big avatar; must be {w}x{h} or smaller').format(w=512, h=512))

        if errors:
            raise ValidationError({'avatar': errors})

        # Выбор формата для сохранения
        if image.format == 'JPEG':
            frmt = 'JPEG'
            ext = 'jpg'
        elif image.format == 'GIF':
            frmt = 'GIF'
            ext = 'gif'
        else:
            frmt = 'PNG'
            ext = 'png'

        result = {}

        # Пути для сохранения
        urlpath = '/'.join(('avatars', str(user.id)))  # equivalent to ospath except Windows!
        ospath = os.path.join(current_app.config['MEDIA_ROOT'], 'avatars', str(user.id))
        prefix = str(int(time.time()) - 1451606400) + '_'
        if not os.path.isdir(ospath):
            os.makedirs(ospath)

        # Обрезка под квадрат
        if image.size[0] > image.size[1]:
            offset = (image.size[0] - image.size[1]) // 2
            cropped = image.crop((offset, 0, image.size[1] + offset, image.size[1]))
        elif image.size[0] < image.size[1]:
            offset = (image.size[1] - image.size[0]) // 2
            cropped = image.crop((0, offset, image.size[0], image.size[0] + offset))
        else:
            cropped = image.copy()

        cropped.load()
        with cropped:
            # Сохраняем три размера
            mindim = min(cropped.size)
            for name, dim in (('small', 24), ('medium', 100), ('large', 256)):
                size = (min(mindim, dim), min(mindim, dim))
                filename = prefix + name + '.' + ext
                result[name] = urlpath + '/' + filename
                filepath = os.path.join(ospath, filename)

                if cropped.size == size:
                    # Если можем, сохраняем картинку как есть
                    if image.size == size and image_data and image.format == frmt:
                        with open(filepath, 'wb') as fp:
                            fp.write(image_data)
                    else:
                        # При отличающемся формате или отсутствии оригинала пересохраняем
                        cropped.save(filepath, frmt, quality=92)
                else:
                    # При неподходящем размере изменяем и сохраняем
                    with cropped.resize(size, Image.ANTIALIAS) as resized:
                        resized.save(filepath, frmt, quality=92)

        # Удаляем старую аватарку с ФС
        self.delete_avatar()

        # Сохраняем в БД
        user.avatar_small = result['small']
        user.avatar_medium = result['medium']
        user.avatar_large = result['large']

        # Возвращаем имена сохранённых файлов
        return result

    def register(self, data):
        from mini_fiction.models import RegistrationProfile

        try:
            data = Validator(REGISTRATION).validated(data)
        except ValidationError as exc:
            if 'email' not in exc.errors and self.is_email_busy(data['email']):
                exc.errors['email'] = [lazy_gettext('Email address is already in use')]
            raise
        data['is_active'] = False
        user = self.create(data)

        rp = RegistrationProfile(
            user=user,
            activation_key=''.join(random.choice(string.ascii_letters + string.digits) for _ in range(40)),
            activated=False,
        )
        rp.flush()

        later(
            current_app.tasks['sendmail'].delay,
            data['email'],
            render_template('email/activation_subject.txt'),
            body={
                'plain': render_template('email/activation.txt', activation_key=rp.activation_key),
                'html': render_template('email/activation.html', activation_key=rp.activation_key),
            },
            headers={'X-Postmaster-Msgtype': current_app.config['EMAIL_MSGTYPES']['registration']},
        )

        return user

    def is_email_busy(self, email):
        return self.model.select(lambda x: x.email.lower() == email.lower()).exists()

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

        later(
            current_app.tasks['sendmail'].delay,
            user.email,
            render_template('email/password_reset_subject.txt'),
            body={
                'plain': render_template('email/password_reset.txt', activation_key=prp.activation_key, user=user),
                'html': render_template('email/password_reset.html', activation_key=prp.activation_key, user=user),
            },
            headers={'X-Postmaster-Msgtype': current_app.config['EMAIL_MSGTYPES']['reset_password']},
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

        if data.startswith('$pbkdf2$'):
            return hashers.pbkdf2_check(data.split('$', 2)[2], password)

        elif data.startswith('$scrypt$'):
            return hashers.scrypt_check(data.split('$', 2)[2], password)

        elif data.startswith('$bcrypt$'):
            return hashers.bcrypt_check(data.split('$', 2)[2], password)

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

        if current_app.config['PASSWORD_HASHER'] == 'pbkdf2':
            user.password = '$pbkdf2$' + hashers.pbkdf2_encode(password)  # $pbkdf2$pbkdf2_sha256$50000$...

        elif current_app.config['PASSWORD_HASHER'] == 'scrypt':
            user.password = '$scrypt$' + hashers.scrypt_encode(password)

        elif current_app.config['PASSWORD_HASHER'] == 'bcrypt':
            user.password = '$bcrypt$' + hashers.bcrypt_encode(password)

        else:
            raise NotImplementedError('Cannot use current password hasher')

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
        if self.model.avatar_medium:
            return url_for('media', filename=self.model.avatar_medium)

        default_userpic = dict(current_app.config['DEFAULT_USERPIC'])
        if 'endpoint' in default_userpic:
            return url_for(default_userpic.pop('endpoint'), **default_userpic)
        else:
            return default_userpic['url']

    def get_small_avatar_url(self):
        if self.model.avatar_small:
            return url_for('media', filename=self.model.avatar_small)

        default_userpic = dict(current_app.config['DEFAULT_USERPIC'])
        if 'endpoint' in default_userpic:
            return url_for(default_userpic.pop('endpoint'), **default_userpic)
        else:
            return default_userpic['url']

    def get_large_avatar_url(self):
        if self.model.avatar_large:
            return url_for('media', filename=self.model.avatar_large)

        default_userpic = dict(current_app.config['DEFAULT_USERPIC'])
        if 'endpoint' in default_userpic:
            return url_for(default_userpic.pop('endpoint'), **default_userpic)
        else:
            return default_userpic['url']
