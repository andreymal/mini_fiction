#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask import current_app, render_template
from flask_babel import lazy_gettext
from pony import orm

from mini_fiction.bl.utils import BaseBL
from mini_fiction.bl.commentable import Commentable
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.news import NEWS_ITEM


class NewsItemBL(BaseBL, Commentable):
    def create(self, author, data):
        data = Validator(NEWS_ITEM).validated(data)

        if not author.is_superuser and data.get('is_template'):
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        if data.get('is_template'):
            self.check_renderability(author, data['name'], data['content'])

        exist_newsitem = self.model.get(name=data['name'])
        if exist_newsitem:
            raise ValidationError({'name': [lazy_gettext('Page already exists')]})

        if data.get('show'):
            self.hide_shown_newsitem()

        newsitem = self.model(author=author, **data)
        newsitem.flush()
        return newsitem

    def update(self, author, data):
        data = Validator(NEWS_ITEM).validated(data, update=True)
        newsitem = self.model

        if not author.is_superuser and (newsitem.is_template or data.get('is_template')):
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        if 'name' in data:
            from mini_fiction.models import NewsItem
            exist_newsitem = NewsItem.get(name=data['name'])
            if exist_newsitem and exist_newsitem.id != newsitem.id:
                raise ValidationError({'name': [lazy_gettext('Page already exists')]})

        if data.get('is_template', newsitem.is_template) and 'content' in data:
            self.check_renderability(author, data.get('name', newsitem.name), data['content'])

        if data.get('show'):
            self.hide_shown_newsitem()

        for key, value in data.items():
            setattr(newsitem, key, value)

        return newsitem

    def delete(self, author):
        self.model.delete()

    def hide_shown_newsitem(self):
        from mini_fiction.models import NewsItem
        n = NewsItem.get(show=True)
        if n:
            n.show = False

    def check_renderability(self, author, name, content):
        try:
            template = current_app.jinja_env.from_string(content)
            template.name = 'db/news/{}.html'.format(name)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot parse news item "{0}": {1}').format(name, str(exc))
            ]})

        from mini_fiction.models import AnonymousUser

        try:
            render_template(template, newsitem_name=name, current_user=AnonymousUser())
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render news item "{0}" for anonymous: {1}').format(name, str(exc))
            ]})

        try:
            render_template(template, newsitem_name=name, current_user=author)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render news item "{0}" for you: {1}').format(name, str(exc))
            ]})

    def has_comments_access(self, author=None):
        from mini_fiction.models import NewsComment
        return NewsComment.bl.has_comments_access(self.model, author)

    def can_comment_by(self, author=None):
        from mini_fiction.models import NewsComment
        return NewsComment.bl.can_comment_by(self.model, author)

    def create_comment(self, author, ip, data):
        from mini_fiction.models import NewsComment
        return NewsComment.bl.create(self.model, author, ip, data)

    def select_comments(self):
        from mini_fiction.models import NewsComment
        return orm.select(c for c in NewsComment if c.newsitem == self.model)

    def select_comment_ids(self):
        from mini_fiction.models import NewsComment
        return orm.select(c.id for c in NewsComment if c.newsitem == self.model)

    def comment2html(self, text):
        from mini_fiction.models import NewsComment
        return NewsComment.bl.text2html(text)

    def select_comment_votes(self, author, comment_ids):
        from mini_fiction.models import NewsCommentVote
        votes = orm.select(
            (v.comment.id, v.vote_value) for v in NewsCommentVote
            if v.author.id == author.id and v.comment.id in comment_ids
        )[:]
        votes = dict(votes)
        return {i: votes.get(i, 0) for i in comment_ids}

    def get_comments_subscription(self, user):
        if not user or not user.is_authenticated:
            return False
        newsitem = self.model
        return user.bl.get_subscription('news_comment', newsitem.id)

    def subscribe_to_comments(self, user, email=None, tracker=None):
        if not user or not user.is_authenticated:
            return False
        newsitem = self.model
        return user.bl.edit_subscription('news_comment', newsitem.id, email=email, tracker=tracker)
