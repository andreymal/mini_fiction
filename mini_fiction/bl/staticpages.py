#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask import current_app, render_template
from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.staticpages import STATIC_PAGE


class StaticPageBL(BaseBL):
    def create(self, author, data):
        from mini_fiction.models import AdminLog

        data = Validator(STATIC_PAGE).validated(data)

        if not author.is_superuser and data.get('is_template'):
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        if data.get('is_template'):
            self.check_renderability(author, data['name'], data['content'])

        if not data.get('lang'):
            data['lang'] = 'none'

        exist_staticpage = self.model.get(name=data['name'], lang=data['lang'])
        if exist_staticpage:
            raise ValidationError({'name': [lazy_gettext('Page already exists')]})

        staticpage = self.model(**data)
        staticpage.flush()
        AdminLog.bl.create(user=author, obj=staticpage, action=AdminLog.ADDITION)
        return staticpage

    def update(self, author, data):
        from mini_fiction.models import AdminLog

        data = Validator(STATIC_PAGE).validated(data, update=True)
        staticpage = self.model

        if not author.is_superuser and (staticpage.is_template or data.get('is_template')):
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        if ('name' in data and data['name'] != staticpage.name) or ('lang' in data and data['lang'] != staticpage.lang):
            raise ValidationError({
                'name': [lazy_gettext('Cannot change primary key')],
                'lang': [lazy_gettext('Cannot change primary key')],
            })

        if data.get('is_template', staticpage.is_template) and 'content' in data:
            self.check_renderability(author, data.get('name', staticpage.name), data['content'])

        changed_fields = set()
        for key, value in data.items():
            if getattr(staticpage, key) != value:
                setattr(staticpage, key, value)
                changed_fields |= {key,}

        if changed_fields:
            AdminLog.bl.create(
                user=author,
                obj=staticpage,
                action=AdminLog.CHANGE,
                fields=sorted(changed_fields),
            )

        return staticpage

    def delete(self, author):
        from mini_fiction.models import AdminLog

        staticpage = self.model
        if staticpage.name in ('help', 'terms', 'robots.txt') and staticpage.lang == 'none':
            raise ValidationError({'is_template': [lazy_gettext('This is system page, you cannot delete it')]})
        if staticpage.is_template and not author.is_superuser:
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        AdminLog.bl.create(user=author, obj=staticpage, action=AdminLog.DELETION)
        staticpage.delete()

    def check_renderability(self, author, name, content):
        try:
            template = current_app.jinja_env.from_string(content)
            template.name = 'db/staticpages/{}.html'.format(name)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot parse staticpage "{0}": {1}').format(name, str(exc))
            ]})

        from mini_fiction.models import AnonymousUser

        try:
            render_template(template, staticpage_name=name, current_user=AnonymousUser())
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render staticpage "{0}" for anonymous: {1}').format(name, str(exc))
            ]})

        try:
            render_template(template, staticpage_name=name, current_user=author)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render staticpage "{0}" for you: {1}').format(name, str(exc))
            ]})

    def get_mimetype(self):
        if self.model.name == 'robots.txt':
            return 'text/plain'
        return 'text/html'
