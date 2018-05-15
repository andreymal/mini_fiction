#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import os
import json
import time
from io import BytesIO
from datetime import datetime, timedelta

from flask import current_app, url_for, render_template
from flask_babel import lazy_gettext

from mini_fiction import hashers
from mini_fiction.utils import random as utils_random
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import ValidationError, Validator
from mini_fiction.validation.auth import REGISTRATION, LOGIN


__all__ = ['AuthorBL']


# Здесь перечислены только те подписки, которые не имеют конкретного target
# Информация о подписке на них хранится в полях Author.silent_*
allowed_subscriptions = {
    'abuse_report',
    'story_pubrequest',
    'story_publish',
    'story_publish_noappr',
    'story_draft',
    'story_delete',
    'story_reply',
    'story_lreply',
    'news_reply',
}


class AuthorBL(BaseBL):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra = None

    def _check_existence(self, username, email):
        errors = {}
        if self.model.select(lambda x: x.username.lower() == username.lower()):
            errors['username'] = [lazy_gettext('User already exists')]
        if email and self.is_email_busy(email):
            errors['email'] = [lazy_gettext('Email address is already in use')]
        return errors

    def create(self, data):
        if 'username' not in data or (not data.get('password') and not data.get('password_hash')):
            raise ValidationError({'username': lazy_gettext('Please set username and password')})

        if data.get('password') and data.get('password_hash'):
            raise ValidationError({'password': lazy_gettext('Please set only password or password hash')})

        errors = {}
        if data.get('password') and current_app.config['CHECK_PASSWORDS_SECURITY'] and not self.is_password_good(data['password'], extra=(data['username'],)):
            errors['password'] = [lazy_gettext('Password is too bad, please change it')]
        errors.update(self._check_existence(data['username'], data['email']))
        if errors:
            raise ValidationError(errors)

        user = self._model()(
            username=data['username'],
            email=data.get('email') or '',
            is_active=bool(data.get('is_active', True)),
            is_staff=bool(data.get('is_staff', False)),
            is_superuser=bool(data.get('is_superuser', False)),
            date_joined=data.get('date_joined', datetime.utcnow()),
            activated_at=data.get('activated_at', None),
            session_token=utils_random.random_string(32),
        )
        user.flush()  # for user.id
        if data.get('password'):
            user.bl.set_password(data['password'])
        else:
            user.password = data['password_hash']
        return user

    def update(self, data, modified_by_user=None, fill_admin_log=False):
        from mini_fiction.models import ChangeEmailProfile

        user = self.model
        changed_fields = set()

        if 'email' in data and data['email'] != user.email:
            user.email = data['email']
            cep = ChangeEmailProfile.get(user=user)
            if cep:
                cep.delete()
            changed_fields |= {'email',}

        for field in ('bio', 'premoderation_mode'):
            if field in data and getattr(user, field) != data[field]:
                setattr(user, field, data[field])
                changed_fields |= {field,}

        for field in ('is_staff', 'is_active', 'is_superuser', 'detail_view', 'nsfw'):
            if field in data and getattr(user, field) != bool(data[field]):
                setattr(user, field, bool(data[field]))
                changed_fields |= {field,}

        if 'excluded_categories' in data:
            user.excluded_categories = ','.join(str(x) for x in data['excluded_categories'])
            changed_fields |= {'excluded_categories',}

        if 'comments_per_page' in data:
            if user.comments_per_page is None and data['comments_per_page'] == current_app.config['COMMENTS_COUNT']['page']:
                pass  # Если бралось значение из настроек проекта, то его и оставляем
            else:
                value = min(1000, max(1, int(data['comments_per_page'])))
                if user.comments_per_page != value:
                    user.comments_per_page = value
                    changed_fields |= {'comments_per_page',}

        if 'comments_maxdepth' in data:
            if user.comments_maxdepth is None and data['comments_maxdepth'] == current_app.config['COMMENTS_TREE_MAXDEPTH']:
                pass  # Если бралось значение из настроек проекта, то его и оставляем
            elif user.comments_maxdepth != int(data['comments_maxdepth']):
                user.comments_maxdepth = int(data['comments_maxdepth'])
                changed_fields |= {'comments_maxdepth',}

        if 'comment_spoiler_threshold' in data:
            if user.comment_spoiler_threshold is None and data['comment_spoiler_threshold'] == current_app.config['COMMENT_SPOILER_THRESHOLD']:
                pass  # Если бралось значение из настроек проекта, то его и оставляем
            elif user.comment_spoiler_threshold != int(data['comment_spoiler_threshold']):
                user.comment_spoiler_threshold = int(data['comment_spoiler_threshold'])
                changed_fields |= {'comment_spoiler_threshold',}

        if data.get('header_mode') in ('off', 'l', 'ls'):
            # off - не показывать картинку в шапке
            # l - показывать только картинку
            # ls - показывать картинку с блоком случайных рассказов
            # Если в базе пусто, то значение по умолчанию ls
            if (user.header_mode or 'ls') != data['header_mode']:
                user.header_mode = data['header_mode']
                changed_fields |= {'header_mode',}

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

            changed_fields |= {'contacts',}  # TODO: надо ли?

        if data.get('delete_avatar'):
            self.delete_avatar()
            changed_fields |= {'avatar_small', 'avatar_medium', 'avatar_large'}

        elif current_app.config['AVATARS_UPLOADING'] and data.get('avatar'):
            from PIL import Image

            image_data = data['avatar'].stream.read(256 * 1024 + 1)
            if len(image_data) > 256 * 1024:
                raise ValidationError({'avatar': [lazy_gettext('Too big avatar; must be {value} KiB or smaller').format(value=256)]})

            try:
                image = Image.open(BytesIO(image_data))
            except Exception:
                raise ValidationError({'avatar': [lazy_gettext('Cannot read avatar')]})
            else:
                with image:
                    self.validate_and_set_avatar(image, image_data)
                changed_fields |= {'avatar_small', 'avatar_medium', 'avatar_large'}

        if data.get('extra') is not None:
            if isinstance(data['extra'], str):
                try:
                    json.loads(data['extra'])
                except Exception:
                    raise ValidationError({'extra': ['Invalid extra JSON']})
                user.extra = data['extra']
                changed_fields |= {'extra',}
            elif not isinstance(data['extra'], dict):
                raise ValidationError({'extra': ['extra must be dict or JSON string']})
            else:
                user.extra = json.dumps(data['extra'], ensure_ascii=False)
                changed_fields |= {'extra',}

        if modified_by_user and fill_admin_log and changed_fields:
            from mini_fiction.models import AdminLog
            AdminLog.bl.create(
                user=modified_by_user,
                obj=user,
                action=AdminLog.CHANGE,
                fields=sorted(changed_fields),
            )

        return changed_fields

    def update_email_subscriptions(self, subs):
        user = self.model

        silent = user.silent_email_list
        modified = []

        for sub in allowed_subscriptions:
            allowed = subs.get(sub)
            if allowed is None:
                continue

            old_allowed = sub not in silent
            if old_allowed != allowed:
                modified.append(sub)
                if allowed:
                    silent.remove(sub)
                else:
                    silent.append(sub)

        if modified:
            user.silent_email = ','.join(silent)
        return modified

    def update_tracker_subscriptions(self, subs):
        user = self.model

        silent = user.silent_tracker_list
        modified = []

        for sub in allowed_subscriptions:
            allowed = subs.get(sub)
            if allowed is None:
                continue

            old_allowed = sub not in silent
            if old_allowed != allowed:
                modified.append(sub)
                if allowed:
                    silent.remove(sub)
                else:
                    silent.append(sub)

        if modified:
            user.silent_tracker = ','.join(silent)
        return modified

    def update_email_with_confirmation(self, email):
        from mini_fiction.models import Author, ChangeEmailProfile

        user = self.model

        cep = ChangeEmailProfile.get(user=user)
        cep_expired = not cep or cep.date + timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS']) < datetime.utcnow()

        if email.lower() == user.email.lower():
            if cep:
                # Отмена установки новой почты
                cep.delete()
            return False

        if Author.bl.is_email_busy(email):
            raise ValidationError({'email': [lazy_gettext('Email address is already in use')]})

        data = {
            'date': datetime.utcnow(),
            'activation_key': utils_random.random_string(40),
            'user': user,
            'email': email,
        }

        if not cep:
            cep = ChangeEmailProfile(**data)
        elif cep_expired or email.lower() != cep.email.lower():
            for k, v in data.items():
                setattr(cep, k, v)

        later(
            current_app.tasks['sendmail'].delay,
            cep.email,
            render_template('email/change_email_subject.txt'),
            body={
                'plain': render_template('email/change_email.txt', activation_key=cep.activation_key, user=user),
                'html': render_template('email/change_email.html', activation_key=cep.activation_key, user=user),
            },
            headers={'X-Postmaster-Msgtype': current_app.config['EMAIL_MSGTYPES']['change_email']},
        )

        if user.email:
            later(
                current_app.tasks['sendmail'].delay,
                user.email,
                render_template('email/change_email_warning_subject.txt'),
                body={
                    'plain': render_template('email/change_email_warning.txt', user=user, new_email=email),
                    'html': render_template('email/change_email_warning.html', user=user, new_email=email),
                },
                headers={'X-Postmaster-Msgtype': current_app.config['EMAIL_MSGTYPES']['change_email_warning']},
            )

        return True

    def get_extra(self, key, default=None):
        if not isinstance(key, str):
            raise ValueError('key must be str')

        if self._extra is None:
            self._extra = json.loads(self.model.extra or '{}')

        return self._extra.get(key, default)

    def set_extra(self, key, value):
        if not isinstance(key, str):
            raise ValueError('key must be str')

        if self._extra is None:
            self._extra = json.loads(self.model.extra or '{}')

        self._extra[key] = value
        self.model.extra = json.dumps(self._extra, ensure_ascii=False)

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

        if current_app.captcha:
            current_app.captcha.check_or_raise(data)

        data = Validator(REGISTRATION).validated(data)
        errors = self._check_existence(data['username'], data['email'])
        if errors:
            raise ValidationError(errors)

        old_rp = RegistrationProfile.get(username=data['username'], email=data['email'])
        if old_rp:
            old_rp.delete()
        del old_rp

        rp = RegistrationProfile(
            activation_key=utils_random.random_string(40),
            email=data['email'],
            password=self.generate_password_hash(data['password']),
            username=data['username'],
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

        return rp

    def is_email_busy(self, email):
        return self.model.select(lambda x: x.email.lower() == email.lower()).exists()

    def generate_password_reset_profile(self):
        from mini_fiction.models import PasswordResetProfile

        user = self.model

        prp = PasswordResetProfile.select(
            lambda x: x.user == user and not x.activated and x.date > datetime.utcnow() - timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS'])
        ).first()
        if prp:
            prp.delete()

        prp = PasswordResetProfile(
            user=user,
            activation_key=utils_random.random_string(40),
            activated=False,
        )
        prp.flush()

        return prp


    def reset_password_by_email(self):
        user = self.model
        if not user.email:
            raise ValueError('User has no email')

        prp = self.generate_password_reset_profile()

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

        if not rp.password or rp.created_at + timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS']) < datetime.utcnow():
            rp.delete()
            return

        tm = datetime.utcnow()

        try:
            user = self.create({
                'email': rp.email,
                'username': rp.username,
                'password_hash': rp.password,
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'date_joined': rp.created_at,
                'activated_at': tm,
            })
        except ValidationError:
            return

        assert rp.username == user.username
        assert rp.email == user.email
        RegistrationProfile.select(lambda x: x.username == user.username).delete(bulk=True)
        RegistrationProfile.select(lambda x: x.email == user.email).delete(bulk=True)
        return user

    def activate_changed_email(self, activation_key):
        from mini_fiction.models import ChangeEmailProfile

        cep = ChangeEmailProfile.get(activation_key=activation_key)
        if not cep:
            return
        user = cep.user

        if not user.is_active or cep.date + timedelta(days=current_app.config['ACCOUNT_ACTIVATION_DAYS']) < datetime.utcnow():
            cep.delete()
            return

        user.email = cep.email
        del cep
        ChangeEmailProfile.select(lambda x: x.email.lower() == user.email.lower()).delete(bulk=True)
        return user

    def authenticate(self, password):
        if not password:
            return False

        if self._model().id == current_app.config['SYSTEM_USER_ID']:
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
            user = self._model().select(lambda x: x.username.lower() == data['username'].lower()).first()
        if not user or not user.bl.authenticate(data['password']):
            raise ValidationError({'username': [lazy_gettext('Please enter a correct username and password.')]})
        if not user.is_active:
            raise ValidationError({'username': [lazy_gettext('Account is disabled')]})
        return user

    def set_password(self, password):
        user = self.model

        if not password and not user.password:
            return

        changed = not self.authenticate(password)
        user.password = self.generate_password_hash(password)
        if changed:
            user.last_password_change = datetime.utcnow()

    def generate_password_hash(self, password):
        if not password:
            return ''

        elif current_app.config['PASSWORD_HASHER'] == 'pbkdf2':
            iterations = current_app.config['PBKDF2_ITERATIONS']
            return '$pbkdf2$' + hashers.pbkdf2_encode(password, iterations=iterations)  # $pbkdf2$pbkdf2_sha256$50000$...

        elif current_app.config['PASSWORD_HASHER'] == 'scrypt':
            return '$scrypt$' + hashers.scrypt_encode(password)

        elif current_app.config['PASSWORD_HASHER'] == 'bcrypt':
            return '$bcrypt$' + hashers.bcrypt_encode(password)

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

    def reset_session_token(self):
        token = utils_random.random_string(32)
        self.model.session_token = token
        return token

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
        return default_userpic['url']

    def get_small_avatar_url(self):
        if self.model.avatar_small:
            return url_for('media', filename=self.model.avatar_small)

        default_userpic = dict(current_app.config['DEFAULT_USERPIC'])
        if 'endpoint' in default_userpic:
            return url_for(default_userpic.pop('endpoint'), **default_userpic)
        return default_userpic['url']

    def get_large_avatar_url(self):
        if self.model.avatar_large:
            return url_for('media', filename=self.model.avatar_large)

        default_userpic = dict(current_app.config['DEFAULT_USERPIC'])
        if 'endpoint' in default_userpic:
            return url_for(default_userpic.pop('endpoint'), **default_userpic)
        return default_userpic['url']

    def get_unread_notifications_count(self):
        user = self.model
        cnt = current_app.cache.get('bell_{}'.format(user.id))
        if cnt is not None:
            return cnt
        cnt = user.notifications.filter(lambda x: x.id > user.last_viewed_notification_id).count()
        current_app.cache.set('bell_{}'.format(user.id), cnt, 600)
        return cnt

    def get_notifications(self, older=None, offset=0, count=100):
        from mini_fiction.models import Notification, Story, Chapter, StoryComment, StoryLocalThread, StoryLocalComment, NewsComment

        user = self.model

        if older is None and offset == 0 and count <= 101:
            result = current_app.cache.get('bell_content_{}'.format(user.id))
            if result is not None:
                return result[:count]

        result = []

        # Забираем уведомления
        items = user.notifications.filter(lambda x: x.id < older) if older is not None else user.notifications
        items = items.order_by(Notification.id.desc()).prefetch(Notification.caused_by_user)[offset:offset + count]

        # Группируем таргеты по типам, чтобы брать их одним sql-запросом
        story_ids = set()
        chapter_ids = set()
        story_comment_ids = set()
        local_comment_ids = set()
        news_comment_ids = set()
        for n in items:
            if n.type in ('story_publish', 'story_draft', 'author_story'):
                story_ids.add(n.target_id)
            elif n.type == 'story_chapter':
                chapter_ids.add(n.target_id)
            elif n.type in ('story_reply', 'story_comment'):
                story_comment_ids.add(n.target_id)
            elif n.type in ('story_lreply', 'story_lcomment'):
                local_comment_ids.add(n.target_id)
            elif n.type in ('news_reply', 'news_comment'):
                news_comment_ids.add(n.target_id)

        # И забираем все эти таргеты
        stories = {
            x.id: x for x in Story.select(
                lambda x: x.id in story_ids
            )
        } if story_ids else {}

        chapters = {
            x.id: x for x in Chapter.select(
                lambda x: x.id in chapter_ids
            )
        } if chapter_ids else {}

        story_comments = {
            x.id: x for x in StoryComment.select(
                lambda x: x.id in story_comment_ids
            ).prefetch(StoryComment.story)
        } if story_comment_ids else {}

        local_comments = {
            x.id: x for x in StoryLocalComment.select(
                lambda x: x.id in local_comment_ids
            ).prefetch(StoryLocalComment.local, StoryLocalThread.story)
        } if local_comment_ids else {}

        news_comments = {
            x.id: x for x in NewsComment.select(
                lambda x: x.id in news_comment_ids
            ).prefetch(NewsComment.newsitem)
        } if news_comment_ids else {}

        # Преобразуем каждое уведомление в json-совместимый формат со всеми дополнениями
        for n in items:
            item = {
                'id': n.id,
                'created_at': n.created_at,
                'type': n.type,
                'viewed': n.id <= user.last_viewed_notification_id,
                'user': {
                    'id': n.caused_by_user.id,
                    'username': n.caused_by_user.username,
                    'is_staff': n.caused_by_user.is_staff,
                } if n.caused_by_user else None,
                'extra': json.loads(n.extra or '{}'),
            }

            if n.type in ('story_publish', 'story_draft', 'author_story'):
                if n.target_id not in stories:
                    item['broken'] = True
                    result.append(item)
                    continue
                item['story'] = {
                    'id': n.target_id,
                    'title': stories[n.target_id].title,
                }
                if n.type == 'author_story':
                    item['story']['words'] = stories[n.target_id].words
                    item['story']['authors'] = [{'id': x.id, 'username': x.username} for x in stories[n.target_id].authors]

            elif n.type == 'story_chapter':
                c = chapters.get(n.target_id)
                if not c:
                    item['broken'] = True
                    result.append(item)
                    continue

                item['story'] = {'id': c.story.id, 'title': c.story.title}
                item['chapter'] = {'id': c.id, 'order': c.order, 'title': c.title, 'autotitle': c.autotitle, 'words': c.words}

            elif n.type in ('story_reply', 'story_comment', 'story_lreply', 'story_lcomment', 'news_reply', 'news_comment'):
                if n.type in ('story_reply', 'story_comment'):
                    c = story_comments.get(n.target_id)
                elif n.type in ('story_lreply', 'story_lcomment'):
                    c = local_comments.get(n.target_id)
                elif n.type in ('news_reply', 'news_comment'):
                    c = news_comments.get(n.target_id)

                if not c:
                    item['broken'] = True
                    result.append(item)
                    continue

                if c.deleted and not user.is_staff:
                    item['comment'] = {
                        'id': c.id,
                        'local_id': c.local_id,
                        'permalink': c.bl.get_permalink(),
                        'can_vote': c.bl.can_vote,
                        'deleted': True,
                    }
                else:
                    item['comment'] = {
                        'id': c.id,
                        'local_id': c.local_id,
                        'permalink': c.bl.get_permalink(),
                        'date': c.date,
                        'brief_text_as_html': str(c.brief_text_as_html),
                        'can_vote': c.bl.can_vote,
                        'deleted': c.deleted,
                        'author': {
                            'id': c.author.id if c.author else None,
                            'username': c.author.username if c.author else c.author_username,
                        }
                    }
                    if hasattr(c, 'vote_total'):
                        item['comment']['vote_total'] = c.vote_total

                if n.type in ('story_reply', 'story_comment'):
                    item['story'] = {'id': c.story.id, 'title': c.story.title}
                elif n.type in ('story_lreply', 'story_lcomment'):
                    item['story'] = {'id': c.local.story.id, 'title': c.local.story.title}
                elif n.type in ('news_reply', 'news_comment'):
                    item['newsitem'] = {'id': c.newsitem.id, 'name': c.newsitem.name, 'title': c.newsitem.title}

            result.append(item)

        if older is None and offset == 0 and count >= 101:
            current_app.cache.set('bell_content_{}'.format(user.id), result[:101], 600)
        return result

    def set_last_viewed_notification_id(self, nid):
        from mini_fiction.models import Notification

        user = self.model

        last_item = user.notifications.select().order_by(Notification.id.desc()).first()
        if last_item:
            if nid > last_item.id:
                nid = last_item.id
        else:
            nid = 0

        if nid > user.last_viewed_notification_id:
            user.last_viewed_notification_id = nid

        current_app.cache.delete('bell_{}'.format(user.id))

    def get_subscription(self, typ, target_id):
        from mini_fiction.models import Subscription

        user = self.model

        sub = Subscription.get(user=user, type=typ, target_id=target_id)
        if not sub:
            return {'email': False, 'tracker': False}
        return {'email': sub.to_email, 'tracker': sub.to_tracker}

    def get_stories_subscription(self, user):
        # Возвращает информацию о подписке user'а на новые рассказы этого пользователя
        if not user or not user.is_authenticated:
            return {'email': False, 'tracker': False}
        author = self.model
        return user.bl.get_subscription('author_story', author.id)

    def subscribe_to_new_stories(self, user, email=None, tracker=None):
        if not user or not user.is_authenticated:
            return False
        author = self.model
        return user.bl.edit_subscription('author_story', author.id, email=email, tracker=tracker)

    def edit_subscription(self, typ, target_id, email=None, tracker=None):
        from mini_fiction.models import Subscription

        user = self.model

        sub = Subscription.get(user=user, type=typ, target_id=target_id)
        if sub:
            old_email = sub.to_email
            old_tracker = sub.to_tracker
        else:
            old_email = False
            old_tracker = False

        new_email = bool(email) if email is not None else old_email
        new_tracker = bool(tracker) if tracker is not None else old_tracker

        if not new_email and not new_tracker:
            if sub:
                sub.delete()
            return True

        if not sub:
            sub = Subscription(
                user=user,
                type=typ,
                target_id=target_id,
                to_email=new_email,
                to_tracker=new_tracker,
            )
        else:
            sub.to_email = new_email
            sub.to_tracker = new_tracker

        return True
