#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask import current_app, render_template
from flask_babel import lazy_gettext
from pony import orm

from mini_fiction.bl.utils import BaseBL
from mini_fiction.bl.commentable import Commentable
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.notices import NOTICE


class NoticeBL(BaseBL, Commentable):
    def create(self, author, data):
        data = Validator(NOTICE).validated(data)

        if not author.is_superuser and data.get('is_template'):
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        if data.get('is_template'):
            self.check_renderability(author, data['name'], data['content'])

        exist_notice = self.model.get(name=data['name'])
        if exist_notice:
            raise ValidationError({'name': [lazy_gettext('Page already exists')]})

        if data.get('show'):
            self.hide_shown_notice()

        notice = self.model(author=author, **data)
        notice.flush()
        return notice

    def update(self, author, data):
        data = Validator(NOTICE).validated(data, update=True)
        notice = self.model

        if not author.is_superuser and (notice.is_template or data.get('is_template')):
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        if 'name' in data:
            from mini_fiction.models import Notice
            exist_notice = Notice.get(name=data['name'])
            if exist_notice and exist_notice.id != notice.id:
                raise ValidationError({'name': [lazy_gettext('Page already exists')]})

        if data.get('is_template', notice.is_template) and 'content' in data:
            self.check_renderability(author, data.get('name', notice.name), data['content'])

        if data.get('show'):
            self.hide_shown_notice()

        for key, value in data.items():
            setattr(notice, key, value)

        return notice

    def delete(self, author):
        self.model.delete()

    def hide_shown_notice(self):
        from mini_fiction.models import Notice
        n = Notice.get(show=True)
        if n:
            n.show = False

    def check_renderability(self, author, name, content):
        try:
            template = current_app.jinja_env.from_string(content)
            template.name = 'db/notices/{}.html'.format(name)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot parse notice "{0}": {1}').format(name, str(exc))
            ]})

        from mini_fiction.models import AnonymousUser

        try:
            render_template(template, notice_name=name, current_user=AnonymousUser())
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render notice "{0}" for anonymous: {1}').format(name, str(exc))
            ]})

        try:
            render_template(template, notice_name=name, current_user=author)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render notice "{0}" for you: {1}').format(name, str(exc))
            ]})

    def can_comment_by(self, author=None):
        from mini_fiction.models import NoticeComment
        return NoticeComment.bl.can_comment_by(self.model, author)

    def select_comments(self):
        from mini_fiction.models import NoticeComment

        return orm.select(c for c in NoticeComment if c.notice == self.model)
