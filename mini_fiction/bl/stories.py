#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import re
import json
import random
import ipaddress
from hashlib import md5
from datetime import datetime, timedelta
from statistics import mean, pstdev

import lxml.html
import lxml.etree
from pony import orm
from flask import Markup, current_app

from mini_fiction.bl.utils import BaseBL
from mini_fiction.bl.commentable import Commentable
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.utils import diff as utils_diff
from mini_fiction.validation import Validator
from mini_fiction.validation.stories import STORY
from mini_fiction.filters import filter_html
from mini_fiction.filters.base import html_doc_to_string
from mini_fiction.filters.html import footnotes_to_html


class StoryBL(BaseBL, Commentable):
    sort_types = {
        0: "weight() DESC, first_published_at DESC",
        1: "first_published_at DESC",
        2: "size DESC",
        3: "id ASC",  # TODO: rating DESC
        4: "comments DESC"
    }

    _contributors = None

    def create(self, authors, data):
        from mini_fiction.models import Category, Character, Classifier, Author, StoryContributor

        if not authors:
            raise ValueError('Authors are required')

        data = Validator(STORY).validated(data)

        approved = not current_app.config['PREMODERATION']
        if authors[0].premoderation_mode == 'on':
            approved = False
        elif authors[0].premoderation_mode == 'off':
            approved = True

        story = self.model(
            title=data['title'],
            summary=data['summary'],
            rating=data['rating'],
            original=data['original'],
            freezed=data['freezed'],
            source_link=data['source_link'],
            source_title=data['source_title'],
            finished=data['finished'],
            notes=data['notes'],
            draft=True,
            approved=approved,
        )
        story.flush()
        story.categories.add(Category.select(lambda x: x.id in data['categories'])[:])
        story.characters.add(Character.select(lambda x: x.id in data['characters'])[:])
        story.classifications.add(Classifier.select(lambda x: x.id in data['classifications'])[:])
        for author in authors:
            StoryContributor(
                story=story,
                user=author,
                is_editor=True,
                is_author=True,
            ).flush()

        story.bl.subscribe_to_comments(authors[0], email=True, tracker=True)
        story.bl.subscribe_to_local_comments(authors[0], email=True, tracker=True)

        later(current_app.tasks['sphinx_update_story'].delay, story.id, ())
        return story

    def edit_log(self, editor, data):
        from mini_fiction.models import StoryLog

        assert isinstance(data, dict)
        for k, v in data.items():
            assert isinstance(k, str)
            assert isinstance(v, list)
            assert len(v) == 2

        sl = StoryLog(
            user=editor,
            story=self.model,
            by_staff=editor.is_staff,
            data_json=json.dumps(data, ensure_ascii=False),
        )

        return sl

    def update(self, editor, data):
        from mini_fiction.models import Category, Character, Classifier, Rating

        data = Validator(STORY).validated(data, update=True)

        story = self.model
        old_published = story.published  # for chapters

        edited_data = {}

        for key in ('title', 'summary', 'notes', 'original', 'finished', 'freezed', 'source_link', 'source_title'):
            if key in data and getattr(story, key) != data[key]:
                edited_data[key] = [getattr(story, key), data[key]]
                setattr(story, key, data[key])

        if 'rating' in data and story.rating.id != data['rating']:
            edited_data['rating'] = [story.rating.id, data['rating']]
            story.rating = Rating.get(id=data['rating'])

        # TODO: refactor
        if 'categories' in data:
            old_value = [x.id for x in story.categories]
            new_value = list(data['categories'])
            if set(old_value) != set(new_value):
                edited_data['categories'] = [old_value, new_value]
                story.categories.clear()
                story.categories.add(Category.select(lambda x: x.id in data['categories'])[:])

        if 'characters' in data:
            old_value = [x.id for x in story.characters]
            new_value = list(data['characters'])
            if set(old_value) != set(new_value):
                edited_data['characters'] = [old_value, new_value]
                story.characters.clear()
                story.characters.add(Character.select(lambda x: x.id in data['characters'])[:])

        if 'classifications' in data:
            old_value = [x.id for x in story.classifications]
            new_value = list(data['classifications'])
            if set(old_value) != set(new_value):
                edited_data['classifications'] = [old_value, new_value]
                story.classifications.clear()
                story.classifications.add(Classifier.select(lambda x: x.id in data['classifications'])[:])

        if edited_data:
            story.updated = datetime.utcnow()
        if editor and edited_data:
            self.edit_log(editor, edited_data)

        if old_published != story.published:
            for c in story.chapters:
                c.story_published = story.published

        later(current_app.tasks['sphinx_update_story'].delay, story.id, ())
        return story

    def approve(self, user, approved):
        story = self.model

        old_approved = story.approved
        if approved == old_approved:
            return

        old_published = story.published

        story.approved = bool(approved)
        if user:
            self.edit_log(user, {'approved': [old_approved, story.approved]})
            if story.approved:
                story.approved_by = user

        notify = user and user.is_staff and not story.draft
        notify = notify and (
            not story.last_author_notification_at or
            story.last_author_notification_at + timedelta(seconds=current_app.config['STORY_NOTIFICATIONS_INTERVAL']) < datetime.utcnow()
        )
        if notify:
            # Уведомляем автора об изменении состояния рассказа
            story.last_author_notification_at = datetime.utcnow()
            story.last_staff_notification_at = None
            later(current_app.tasks['notify_story_publish_draft'].delay, story.id, user.id, not story.published)

        if old_published != story.published:
            if story.published and not story.first_published_at:
                story.first_published_at = datetime.utcnow()
            later(current_app.tasks['sphinx_update_story'].delay, story.id, ('approved', 'first_published_at'))

            published_chapter_ids = []
            for c in sorted(story.chapters, key=lambda c: c.order):
                c.story_published = story.published
                if story.published and not c.draft and not c.first_published_at:
                    c.first_published_at = datetime.utcnow()
                    published_chapter_ids.append(c.id)
                later(current_app.tasks['sphinx_update_chapter'].delay, c.id)

            if published_chapter_ids:
                later(current_app.tasks['notify_story_chapters'].delay, published_chapter_ids, user.id if user else None)

            for c in story.comments:  # TODO: update StoryComment where story = story.id
                c.story_published = story.published

    def publish(self, user, published):
        story = self.model
        old_published = story.published

        old_draft = story.draft
        if (not published) == story.draft:
            return True

        if story.publishable or (not story.draft and not story.publishable):
            story.draft = not published

            if user:
                self.edit_log(user, {'draft': [old_draft, story.draft]})

            if not story.draft and user and not user.is_staff:
                story.published_by_author = user

            # Уведомление о запросе публикации, если:
            # 1) Это запросил обычный пользователь
            notify_pubrequest = user and not story.draft and not story.approved and not user.is_staff
            # 2) С момента предыдущего запроса прошло достаточно времени (защита от email-флуда)
            notify_pubrequest = notify_pubrequest and (
                not story.last_staff_notification_at or
                story.last_staff_notification_at + timedelta(seconds=current_app.config['STORY_NOTIFICATIONS_INTERVAL']) < datetime.utcnow()
            )

            if notify_pubrequest:
                story.last_staff_notification_at = datetime.utcnow()
                story.last_author_notification_at = None
                later(current_app.tasks['notify_story_pubrequest'].delay, story.id, user.id)

            # Уведомление автора о скрытии рассказа модератором, если:
            # 1) Если это и правда модератор
            notify_draft = user and user.is_staff
            # 2) Рассказ был опубликован
            notify_draft = notify_draft and (old_published and story.draft)
            # 3) С момента предыдущего уведомления прошло достаточно времени
            notify_draft = notify_draft and (
                not story.last_author_notification_at or
                story.last_author_notification_at + timedelta(seconds=current_app.config['STORY_NOTIFICATIONS_INTERVAL']) < datetime.utcnow()
            )

            if notify_draft:
                story.last_author_notification_at = datetime.utcnow()
                story.last_staff_notification_at = None
                later(current_app.tasks['notify_story_publish_draft'].delay, story.id, user.id, not story.published)

            # Уведомление модераторов о публикации рассказа, если:
            # 1) Его опубликовал обычный пользователь
            notify_publish_noappr = user and not user.is_staff
            # 2) Рассказ опубликован и ранее был автоматически одобрен (отключенная премодерация)
            notify_publish_noappr = notify_publish_noappr and story.published and not story.approved_by
            # 3) Рассказ ранее не публиковался
            notify_publish_noappr = notify_publish_noappr and not story.first_published_at

            if notify_publish_noappr:
                later(current_app.tasks['notify_story_publish_noappr'].delay, story.id, user.id)

            # Прочие действия, в том числе проставление first_published_at
            if old_published != story.published:
                if story.published and not story.first_published_at:
                    story.first_published_at = datetime.utcnow()
                later(current_app.tasks['sphinx_update_story'].delay, story.id, ('draft', 'first_published_at'))

                published_chapter_ids = []
                for c in sorted(story.chapters, key=lambda c: c.order):
                    c.story_published = story.published
                    if story.published and not c.draft and not c.first_published_at:
                        c.first_published_at = datetime.utcnow()
                        published_chapter_ids.append(c.id)
                    later(current_app.tasks['sphinx_update_chapter'].delay, c.id)

                if published_chapter_ids:
                    later(current_app.tasks['notify_story_chapters'].delay, published_chapter_ids, user.id if user else None)

                for c in story.comments:
                    c.story_published = story.published
            return True

        return False

    def publish_all_chapters(self, user=None):
        story = self.model
        published_chapter_ids = []
        for c in sorted(story.chapters, key=lambda x: x.order):
            if not c.draft:
                continue
            story.words += c.words
            c.draft = False
            later(current_app.tasks['sphinx_update_chapter'].delay, c.id)
            if story.published and not c.first_published_at:
                c.first_published_at = datetime.utcnow()
                published_chapter_ids.append(c.id)

        if published_chapter_ids:
            later(current_app.tasks['notify_story_chapters'].delay, published_chapter_ids, user.id if user else None)

    def delete(self, user=None):
        from mini_fiction.models import StoryComment, StoryLocalComment, Subscription, Notification

        story = self.model
        later(current_app.tasks['sphinx_delete_story'].delay, story.id)

        # При необходимости уведомляем модераторов об удалении
        # (учтите, что код отправки уведомления выполнится не сейчас, а после удаления)
        if story.approved and story.first_published_at:
            later(
                current_app.tasks['notify_story_delete'].delay,
                story_id=story.id,
                story_title=story.title,
                user_id=user.id if user else None,
                approved_by_id=story.approved_by.id if story.approved and story.approved_by else None,
            )

        # Pony ORM не осиливает сложный каскад, помогаем
        # (StoryLog зависит от Chapter и от Story, Pony ORM пытается удалить
        # Chapter раньше, и БД ругается, что у него ещё есть зависимые StoryLog)
        # https://github.com/ponyorm/pony/issues/278
        story.edit_log.select().delete(bulk=True)

        story_id = story.id  # Вроде бы обход утечки памяти
        local_thread_id = story.local.id if story.local else None

        # Неявная связь с подписками
        Subscription.select(
            lambda x: x.type in ('story_comment', 'story_lcomment') and x.target_id == story_id
        ).delete(bulk=True)

        # Неявная связь с уведомлениями
        Notification.select(
            lambda x: x.type in ('story_publish', 'story_draft') and x.target_id == story_id
        ).delete(bulk=True)

        comment_ids = orm.select(x.id for x in StoryComment if x.story.id == story_id)
        Notification.select(
            lambda x: x.type in ('story_reply', 'story_comment') and x.target_id in comment_ids
        ).delete(bulk=True)

        if local_thread_id is not None:
            local_comment_ids = orm.select(x.id for x in StoryLocalComment if x.local.id == local_thread_id)
            Notification.select(
                lambda x: x.type in ('story_lreply', 'story_lcomment') and x.target_id in local_comment_ids
            ).delete(bulk=True)

        # Остальные связи Pony ORM осилит
        story.delete()

    def viewed(self, user):
        if not user.is_authenticated:
            return

        from mini_fiction.models import Activity

        story = self.model
        last_comment = self.select_comments().order_by('-c.id').first()
        data = {
            'last_views': story.views,
            'last_comments': story.comments_count,
            'last_vote_average': story.vote_average,
            'last_vote_stddev': story.vote_stddev,
            'last_comment_id': last_comment.id if last_comment else 0,
        }
        act = Activity.get(story=story, author=user)
        if not act:
            act = Activity(story=story, author=user, **data)
        else:
            for k, v in data.items():
                setattr(act, k, v)
        return act

    def vote(self, user, value, ip):
        from mini_fiction.models import Vote

        story = self.model
        if self.is_author(user):
            raise ValueError('Нельзя голосовать за свой рассказ')
        if value < 1 or value > 5:
            raise ValueError('Неверное значение')

        ip = ipaddress.ip_address(ip).exploded

        vote = Vote.select(lambda x: x.author == user and x.story == story).first()
        if not vote:
            vote = Vote(
                author=user,
                story=story,
                vote_value=value,
                ip=ip,
            )
        elif value != vote.vote_value:
            vote.vote_value = value
            vote.ip = ip
        vote.flush()
        self._update_rating()

        return vote

    def _update_rating(self):
        from mini_fiction.models import Vote

        story = self.model
        votes = orm.select(x.vote_value for x in Vote if x.story == story).without_distinct()[:]
        m = mean(votes)
        story.vote_average = m
        story.vote_stddev = pstdev(votes, m)
        story.vote_total = len(votes)
        story.flush()

    def can_show_stars(self):
        story = self.model
        return story.vote_total >= current_app.config['STARS_MINIMUM_VOTES']

    def stars(self):
        if not self.can_show_stars():
            return [6, 6, 6, 6, 6]

        story = self.model
        stars = []
        avg = story.vote_average
        devmax = avg + story.vote_stddev

        for i in range(1, 6):
            if avg >= i - 0.25:
                # полная звезда
                stars.append(5)
            elif avg >= i - 0.75:
                # половина звезды
                stars.append(4 if devmax >= i - 0.25 else 3)
            elif devmax >= i - 0.25:
                # пустая звезда (с полным отклонением)
                stars.append(2)
            else:
                # пустая звезда (с неполным отклонением)
                stars.append(1 if devmax >= i - 0.75 else 0)

        return stars

    def get_all_views_for_author(self, author):
        # TODO: optimize it
        from mini_fiction.models import StoryContributor, StoryView

        story_ids = orm.select(x.story.id for x in StoryContributor if x.user == author and x.is_author)
        return StoryView.select(lambda x: x.story.id in story_ids).count()

    def select_accessible(self, user):
        cls = self.model
        default_queryset = cls.select(lambda x: x.approved and not x.draft)
        if not user or not user.is_authenticated:
            return default_queryset
        if user.is_staff:
            return cls.select()
        else:
            return default_queryset

    def select_by_author(self, author, for_user=None):
        from mini_fiction.models import StoryContributor

        if not for_user or not for_user.is_authenticated or not for_user.is_staff:
            return orm.select(y.story for y in StoryContributor if y.user == author and y.is_author and not y.story.draft and y.story.approved)

        return orm.select(y.story for y in StoryContributor if y.user == author and y.is_author)

    def select_accessible_chapters(self, user):
        default_queryset = self.model.chapters.filter(lambda x: not x.draft)
        if not user or not user.is_authenticated:
            return default_queryset
        if user.is_staff or self.is_contributor(user):
            return self.model.chapters
        return default_queryset

    def edit_contributors(self, contributors):
        from mini_fiction.models import Author, StoryContributor

        objs = {x.user.id: x for x in self.get_contributors()}
        for user_id, acc in contributors.items():
            user = Author.get(id=user_id)
            if not user:
                raise ValueError('User not found')

            if acc is None:
                if user_id in objs:
                    objs.pop(user_id).delete()
                continue

            if user_id not in objs:
                objs[user_id] = StoryContributor(
                    story=self.model,
                    user=user,
                    visible=acc['is_author'] or acc.get('visible', False),
                    is_editor=acc['is_editor'],
                    is_author=acc['is_author'],
                )
                objs[user_id].flush()
            else:
                objs[user_id].visible = acc['is_author'] or acc.get('visible', False)
                objs[user_id].is_editor = acc['is_editor']
                objs[user_id].is_author = acc['is_author']

        self._contributors = None


    # access control

    def get_contributors(self):
        from mini_fiction.models import StoryContributor

        if self._contributors is None:
            self._contributors = sorted(self.model.contributors, key=lambda x: x.id)
        return self._contributors

    def get_contributors_for_view(self):
        result = {
            'betas': [],
            'editors': [],
            'authors': [],
        }

        for x in self.get_contributors():
            if not x.visible and not x.is_author:
                continue
            if x.is_author:
                result['authors'].append(x.user)
            elif x.is_editor:
                result['editors'].append(x.user)
            else:
                result['betas'].append(x.user)

        return result

    def get_authors(self):
        return [x.user for x in self.get_contributors() if x.is_author]

    def get_editors(self):
        return [x.user for x in self.get_contributors() if x.is_editor]

    def is_contributor(self, user):
        return (
            user and user.is_authenticated and
            user in [x.user for x in self.get_contributors()]
        )

    def is_author(self, user):
        return (
            user and user.is_authenticated and
            user in self.get_authors()
        )

    def is_editor(self, user):
        return (
            user and user.is_authenticated and
            user in self.get_editors()
        )

    def editable_by(self, user):
        return user and (user.is_staff or self.is_editor(user))

    def publishable_by(self, user):
        return user and (user.is_staff or self.is_editor(user) and self.is_author(user))

    def can_edit_contributors(self, user):
        return user and (user.is_staff or self.is_editor(user) and self.is_author(user))

    def can_view_editlog(self, user):
        if user and user.is_staff:
            return True
        return self.is_contributor(user)

    def deletable_by(self, user):
        allowed_user = None
        for c in self.get_contributors():
            if c.is_editor and c.is_author:
                allowed_user = c.user
                break
        return user and user == allowed_user

    def has_access(self, user):
        story = self.model
        if user and user.is_staff:
            return True
        if story.published or self.is_contributor(user):
            return True
        return False

    def has_beta_access(self, user):
        if user and user.is_staff:
            return True
        if self.is_contributor(user):
            return True
        return False

    # search

    def add_stories_to_search(self, stories):
        if current_app.config['SPHINX_DISABLED']:
            return
        stories = [{
            'id': story.id,
            'title': story.title,
            'summary': story.summary,
            'notes': story.notes,
            'first_published_at': int(((story.first_published_at or story.date) - datetime(1970, 1, 1, 0, 0, 0)).total_seconds()),
            'rating_id': story.rating.id,
            'size': story.words,
            'comments': story.comments_count,
            'finished': story.finished,
            'original': story.original,
            'freezed': story.freezed,
            'published': story.published,
            'character': [x.id for x in story.characters],  # TODO: check performance
            'category': [x.id for x in story.categories],
            'classifier': [x.id for x in story.classifications],
            'match_author': ' '.join(x.username for x in story.authors),
            'author': [x.id for x in story.authors],
        } for story in stories]

        with current_app.sphinx as sphinx:
            sphinx.add('stories', stories)

    def delete_stories_from_search(self, story_ids):
        if current_app.config['SPHINX_DISABLED']:
            return
        with current_app.sphinx as sphinx:
            sphinx.delete('stories', id__in=story_ids)
        with current_app.sphinx as sphinx:
            sphinx.delete('chapters', story_id__in=story_ids)

    def search_add(self):
        self.add_stories_to_search((self.model,))

    def search_update(self, update_fields=()):
        if current_app.config['SPHINX_DISABLED']:
            return
        story = self.model
        f = set(update_fields)
        if f and not f - {'vote_average', 'vote_stddev', 'vote_total'}:
            pass  # TODO: рейтинг
        elif f and not f - {'date', 'first_published_at', 'draft', 'approved'}:
            with current_app.sphinx as sphinx:
                timestamp = ((story.first_published_at or story.date) - datetime(1970, 1, 1, 0, 0, 0)).total_seconds()
                sphinx.update('stories', fields={'first_published_at': int(timestamp), 'published': int(story.published)}, id=story.id)
                sphinx.update('chapters', fields={'first_published_at': int(timestamp), 'published': int(story.published)}, id__in=[x.id for x in story.chapters])
        elif f == {'words'}:
            with current_app.sphinx as sphinx:
                sphinx.update('stories', fields={'size': int(story.words)}, id=story.id)
        elif f == {'comments'}:
            with current_app.sphinx as sphinx:
                sphinx.update('stories', fields={'comments': int(story.comments_count)}, id=story.id)
        else:
            with current_app.sphinx as sphinx:
                self.add_stories_to_search((story,))

    def search_delete(self):
        self.delete_stories_from_search((self.model.id,))

    def search(self, query, limit, sort_by=0, only_published=True, **filters):
        if current_app.config['SPHINX_DISABLED']:
            return {}, []

        if sort_by not in self.sort_types:
            sort_by = 0

        sphinx_filters = {}
        if only_published:
            sphinx_filters['published'] = 1

        # TODO: unused, remove it?
        # for ofilter in ('character', 'classifier', 'category', 'rating_id'):
        #     if filters.get(ofilter):
        #         sphinx_filters[ofilter + '__in'] = [x.id for x in filters[ofilter]]

        for ifilter in ('original', 'finished', 'freezed', 'character', 'classifier', 'category', 'rating_id'):
            if filters.get(ifilter):
                sphinx_filters[ifilter + '__in'] = [int(x) for x in filters[ifilter]]

        if filters.get('excluded_categories'):
            sphinx_filters['category__not_in'] = [int(x) for x in filters['excluded_categories']]

        if filters.get('min_words') is not None:
            sphinx_filters['size__gte'] = int(filters['min_words'])

        if filters.get('max_words') is not None:
            sphinx_filters['size__lte'] = int(filters['max_words'])

        with current_app.sphinx as sphinx:
            raw_result = sphinx.search(
                'stories',
                query,
                weights=current_app.config['SPHINX_CONFIG']['weights_stories'],
                options=current_app.config['SPHINX_CONFIG']['select_options'],
                limit=limit,
                sort_by=self.sort_types[sort_by],
                **sphinx_filters
            )

        ids = [x['id'] for x in raw_result['matches']]
        result = {x.id: x for x in self.model.select(lambda x: x.id in ids)}
        result = [result[i] for i in ids if i in result]

        return raw_result, result

    # comments

    def has_comments_access(self, author=None):
        from mini_fiction.models import StoryComment
        return StoryComment.bl.has_comments_access(self.model, author)

    def can_comment_by(self, author=None):
        from mini_fiction.models import StoryComment
        return StoryComment.bl.can_comment_by(self.model, author)

    def create_comment(self, author, ip, data):
        from mini_fiction.models import StoryComment
        return StoryComment.bl.create(self.model, author, ip, data)

    def select_comments(self):
        from mini_fiction.models import StoryComment
        return orm.select(c for c in StoryComment if c.story == self.model)

    def comment2html(self, text):
        from mini_fiction.models import StoryComment
        return StoryComment.bl.text2html(text)

    def select_comment_votes(self, author, comment_ids):
        from mini_fiction.models import StoryCommentVote
        votes = orm.select(
            (v.comment.id, v.vote_value) for v in StoryCommentVote
            if v.author.id == author.id and v.comment.id in comment_ids
        )[:]
        votes = dict(votes)
        return {i: votes.get(i, 0) for i in comment_ids}

    def last_viewed_comment_by(self, author):
        if author and author.is_authenticated:
            act = self.model.activity.select(lambda x: x.author.id == author.id).first()
            return act.last_comment_id if act else None
        else:
            return None

    def get_subscription(self, user):
        if not user or not user.is_authenticated:
            return False
        story = self.model
        return user.bl.get_subscription('story_chapter', story.id)

    def subscribe(self, user, email=None, tracker=None):
        if not user or not user.is_authenticated:
            return False
        story = self.model
        return user.bl.edit_subscription('story_chapter', story.id, email=email, tracker=tracker)

    def get_comments_subscription(self, user):
        if not user or not user.is_authenticated:
            return False
        story = self.model
        return user.bl.get_subscription('story_comment', story.id)

    def subscribe_to_comments(self, user, email=None, tracker=None):
        if not user or not user.is_authenticated:
            return False
        story = self.model
        return user.bl.edit_subscription('story_comment', story.id, email=email, tracker=tracker)

    def get_local_comments_subscription(self, user):
        if not user or not user.is_authenticated:
            return False
        story = self.model
        return user.bl.get_subscription('story_lcomment', story.id)

    def subscribe_to_local_comments(self, user, email=None, tracker=None):
        if not user or not user.is_authenticated:
            return False
        story = self.model
        return user.bl.edit_subscription('story_lcomment', story.id, email=email, tracker=tracker)

    # local comments (through StoriesLocalThread)

    def get_or_create_local_thread(self):
        from mini_fiction.models import StoryLocalThread

        story = self.model
        if story.local:
            return story.local

        local = StoryLocalThread(story=story)
        local.flush()
        assert story.local == local
        return local

    def viewed_localcomments(self, user):
        if not user or not user.is_authenticated:
            return

        from mini_fiction.models import Activity

        act = Activity.get(story=self.model, author=user)
        if not act:
            return

        local = self.get_or_create_local_thread()

        act.last_local_comments = local.comments_count
        last_comment = local.bl.select_comments().order_by('-c.id').first()
        act.last_local_comment_id = last_comment.id if last_comment else 0

        return act

    def last_viewed_local_comment_by(self, author):
        if author and author.is_authenticated:
            act = self.model.activity.select(lambda x: x.author.id == author.id).first()
            return act.last_local_comment_id if act else None
        else:
            return None

    # misc

    def get_random(self, count=10):
        # это быстрее, чем RAND() в MySQL
        from mini_fiction.models import Story, Character, Category
        Story = self.model
        ids = current_app.cache.get('all_story_ids')
        if not ids:
            ids = orm.select((x.id, x.date) for x in Story if x.approved and not x.draft).order_by(2)
            ids = [x[0] for x in ids]
            current_app.cache.set('all_story_ids', ids, 300)
        if len(ids) > count:
            ids = random.sample(ids, count)
        stories = Story.select(lambda x: x.id in ids).prefetch(Story.characters, Story.categories)[:]
        random.shuffle(stories)
        return stories


class StoryLocalThreadBL(BaseBL, Commentable):
    def has_comments_access(self, author=None):
        from mini_fiction.models import StoryLocalComment
        return StoryLocalComment.bl.has_comments_access(self.model, author)

    def can_comment_by(self, author=None):
        from mini_fiction.models import StoryLocalComment
        return StoryLocalComment.bl.can_comment_by(self.model, author)

    def create_comment(self, author, ip, data):
        from mini_fiction.models import StoryLocalComment
        return StoryLocalComment.bl.create(self.model, author, ip, data)

    def select_comments(self):
        from mini_fiction.models import StoryLocalComment
        return orm.select(c for c in StoryLocalComment if c.local == self.model)

    def comment2html(self, text):
        from mini_fiction.models import StoryLocalComment
        return StoryLocalComment.bl.text2html(text)


class ChapterBL(BaseBL):
    def create(self, story, editor, data):
        from mini_fiction.models import Chapter

        new_order = orm.select(orm.max(x.order) for x in Chapter if x.story == story).first()

        text = data['text'].replace('\r', '').strip()

        chapter = self.model(
            story=story,
            title=data['title'],
            notes=data['notes'],
            text=text,
            text_md5=md5(text.encode('utf-8')).hexdigest(),
            draft=True,
            story_published=story.published,
        )
        chapter.order = (new_order or 0) + 1

        self._update_words_count(chapter)
        chapter.flush()
        chapter.bl.edit_log(editor, 'add', {}, text_md5=chapter.text_md5)
        story.updated = datetime.utcnow()
        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        return chapter

    def edit_log(self, editor, action, data, chapter_text_diff=None, text_md5=None):
        from mini_fiction.models import StoryLog

        chapter = self.model

        assert isinstance(data, dict)
        for k, v in data.items():
            assert isinstance(k, str)
            assert isinstance(v, (list, tuple))
            assert len(v) == 2

        sl = StoryLog(
            user=editor,
            story=chapter.story,
            chapter_action=action,
            chapter=chapter,
            chapter_title=chapter.title,
            by_staff=editor.is_staff,
            data_json=json.dumps(data, ensure_ascii=False),
            chapter_text_diff=json.dumps(chapter_text_diff, ensure_ascii=False) if chapter_text_diff is not None else '',
            chapter_md5=text_md5 or '',
        )

        return sl

    def update(self, editor, data):
        chapter = self.model
        edited_data = {}
        chapter_text_diff = None

        if 'title' in data and data['title'] != chapter.title:
            edited_data['title'] = [chapter.title, data['title']]
            chapter.title = data['title']

        if 'notes' in data and data['notes'] != chapter.notes:
            edited_data['notes'] = [chapter.notes, data['notes']]
            chapter.notes = data['notes']

        text = data['text'].replace('\r', '').strip() if 'text' in data else None

        if 'text' in data and text != chapter.text:
            if len(chapter.text) <= current_app.config['MAX_SIZE_FOR_DIFF'] and len(text) <= current_app.config['MAX_SIZE_FOR_DIFF']:
                # Для небольших текстов используем дифф на питоне, который красивый, но не быстрый
                chapter_text_diff = utils_diff.get_diff_default(chapter.text, text)
            else:
                try:
                    # Для больших текстов используем библиотеку на C++, которая даёт диффы быстро, но не очень красиво
                    import diff_match_patch  # pylint: disable=W0612
                except ImportError:
                    # Если библиотеки нет, то и дифф не получился
                    chapter_text_diff = [('-', chapter.text), ('+', text)]
                else:
                    chapter_text_diff = utils_diff.get_diff_google(chapter.text, text)

            chapter.text = text
            chapter.text_md5 = md5(text.encode('utf-8')).hexdigest()
            self._update_words_count(chapter)

        if edited_data or chapter_text_diff:
            chapter.updated = datetime.utcnow()
            chapter.story.updated = datetime.utcnow()
            chapter.bl.edit_log(editor, 'edit', edited_data, chapter_text_diff=chapter_text_diff, text_md5=chapter.text_md5)

        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        return chapter

    def _update_words_count(self, chapter):
        old_words = chapter.words
        new_words = len(Markup.striptags(chapter.text.replace('<', ' <')).split())
        if new_words != chapter.words:
            chapter.words = new_words
            if not chapter.draft:
                story = chapter.story
                story.words = story.words - old_words + new_words

    def delete(self, editor):
        from mini_fiction.models import Chapter

        chapter = self.model
        story = chapter.story
        story.words = story.words - chapter.words
        later(current_app.tasks['sphinx_delete_chapter'].delay, story.id, chapter.id)

        old_order = chapter.order
        chapter.bl.edit_log(editor, 'delete', {})
        chapter.delete()

        for c in Chapter.select(lambda x: x.story == story and x.order > old_order):
            c.order = c.order - 1

        story.updated = datetime.utcnow()

    def notes2html(self, notes):
        if not notes:
            return Markup('')
        try:
            doc = filter_html(notes)
            return Markup(html_doc_to_string(doc))
        except Exception:
            import sys
            import traceback
            print("filter_html_notes", file=sys.stderr)
            traceback.print_exc()
            return "#ERROR#"

    def filter_text(self, text):
        text = text.replace('\r', '')
        return filter_html(
            text,
            tags=current_app.config['CHAPTER_ALLOWED_TAGS'],
            attributes=current_app.config['CHAPTER_ALLOWED_ATTRIBUTES'],
        )

    def filter_text_for_preview(self, text, start, end):
        text = text.replace('\r', '')

        # Для качественного предпросмотра куска текста нужно учитывать все
        # родительские теги, в которые вложен требуемый кусок. Для этого мы
        # парсим весь текст целиком, но помечаем начало и конец специальными
        # тегами, а потом в выводе берём только содержимое между этими тегами
        # вместе с их родителями

        buf = []

        # Наш специальный тег будет случайным, чтобы клиент случайно или
        # намеренно не мог воткнуть его сам
        tag_prefix = 'preview-' + str(random.randrange(10 ** 9, 10 ** 10))
        tag_start = '{0}-start'.format(tag_prefix)
        tag_end = '{0}-end'.format(tag_prefix)

        # Вставляем тег-начало
        f1 = text.rfind('<', 0, start)
        f2 = text.find('>', f1) if f1 >= 0 else -1

        # Если начало внутри тега, то переносим его перед тегом
        if f2 >= start:
            start = f1

        buf.append(text[:start])
        buf.append('<{0}></{0}>'.format(tag_start))

        # Вставляем тег-конец
        f1 = text.rfind('<', start, end)
        f2 = text.find('>', f1) if f1 >= 0 else -1

        # Если конец внутри тега, то переносим его после тега
        if f2 >= end:
            end = f2 + 1
        buf.append(text[start:end])
        buf.append('<{0}></{0}>'.format(tag_end))
        buf.append(text[end:])

        prepared_text = ''.join(buf)

        # Фильтруем HTML как обычно, но с нашими доп. тегами
        doc = filter_html(
            prepared_text,
            tags=list(current_app.config['CHAPTER_ALLOWED_TAGS']) + [tag_start, tag_end],
            attributes=current_app.config['CHAPTER_ALLOWED_ATTRIBUTES'],
        )

        # Достаём тег, с которого начинать, и делаем его чистую копию
        # со всеми родителями — внутри него будет лежать кусок, нужный для
        # предпросмотра
        doc_part = None
        x = doc.xpath('//' + tag_start)[0]
        while x.getparent() is not None:
            p = x.getparent()
            x2 = lxml.html.Element(p.tag)
            for k, v in p.attrib.items():
                x2.set(k, v)
            if doc_part is not None:
                x2.append(doc_part)
            doc_part = x2
            del x2
            x = p
        assert doc_part is not None

        # TODO: по-хорошему надо бы делать это через DOM, но обработка строки
        # тупо проще пишется
        html = lxml.html.tostring(doc, encoding='utf-8').decode('utf-8')

        # Выдираем из HTML-кода кусок, нужный для предпросмотра
        # (код прогнан через lxml и полностью валиден и предсказуем, так что
        # так делать можно)
        html_content = html.split('<{0}></{0}>'.format(tag_start), 1)[1]
        html_content = html_content.split('<{0}></{0}>'.format(tag_end), 1)[0]

        # Выдираем HTML-теги, которые запихнём перед тем куском
        # <foo><bar></bar></foo> → <foo><bar>
        html_before = lxml.html.tostring(doc_part, encoding='utf-8').decode('utf-8')
        f = html_before.find('</')
        f2 = html_before.find('/>')
        if f < 0 or f2 >= 0 and f2 < f:
            f = f2
        assert f > 0
        html_before = html_before[:f]

        # Соединяем это всё и получаем готовый предпросмотр
        # (закрывающие теги lxml добавит сам после парсинга)
        html_part = html_before + html_content

        return lxml.etree.HTML(html_part)

    def text2html(self, text, start=None, end=None):
        if not text:
            return Markup('')
        try:
            if start is not None and end is not None and start < end and start >= 0 and start < len(text) - 1:
                doc = self.filter_text_for_preview(text, start, end)
            else:
                doc = self.filter_text(text)
            doc = footnotes_to_html(doc)
            return Markup(html_doc_to_string(doc))
        except Exception:
            import traceback
            if current_app.config['DEBUG']:
                return traceback.format_exc()
            else:
                traceback.print_exc()
            return "#ERROR#"

    def get_version(self, text_md5=None, log_item=None):
        from mini_fiction.models import StoryLog

        chapter = self.model

        if bool(text_md5) == bool(log_item):
            raise ValueError('Please set text_md5 or log_item')

        if text_md5:
            log_item = StoryLog.select(lambda x: x.chapter == chapter and x.chapter_md5 == text_md5)
            log_item = log_item.order_by(StoryLog.id.desc()).first()
            if not log_item:
                return None
        else:
            text_md5 = log_item.chapter_md5
            if not text_md5:
                raise ValueError('This log_item has no chapter md5')

        # Если md5 совпадает с текущим текстом, то его и возвращаем
        if chapter.text_md5 == text_md5:
            return chapter.text

        # Если не совпало, то собираем диффы с логов для отката с новой версии на старую
        logs = orm.select(
            (x.created_at, x.chapter_text_diff) for x in StoryLog
            if x.chapter == chapter and x.created_at >= log_item.created_at
        ).order_by(-1)[:]

        chapter_text = chapter.text
        # Последовательно откатываем более новые изменения у нового текста, получая таким образом старый
        for x in logs[:-1]:
            if not x[1]:
                continue
            chapter_text = utils_diff.revert_diff(chapter_text, json.loads(x[1]))

        # И в итоге получаем требуемый старый текст
        assert md5(chapter_text.encode('utf-8')).hexdigest() == text_md5
        return chapter_text

    def get_diff_from_older_version(self, older_md5):
        chapter = self.model
        if chapter.text_md5 == older_md5:
            return chapter.text, []

        older_text = self.get_version(text_md5=older_md5)
        if older_text is None:
            return None, []

        if len(older_text) <= current_app.config['MAX_SIZE_FOR_DIFF'] and len(chapter.text) <= current_app.config['MAX_SIZE_FOR_DIFF']:
            # Для небольших текстов используем дифф на питоне, который красивый, но не быстрый
            chapter_text_diff = utils_diff.get_diff_default(older_text, chapter.text)
        else:
            try:
                # Для больших текстов используем библиотеку на C++, которая даёт диффы быстро, но не очень красиво
                import diff_match_patch  # pylint: disable=W0612
            except ImportError:
                # Если библиотеки нет, то и дифф не получился
                chapter_text_diff = [('-', older_text), ('+', chapter.text)]
            else:
                chapter_text_diff = utils_diff.get_diff_google(older_text, chapter.text)

        return older_text, chapter_text_diff

    def publish(self, user, published):
        chapter = self.model
        story = chapter.story
        if published == (not chapter.draft):
            return

        chapter.draft = not published

        if user:
            self.edit_log(user, 'edit', {'draft': [not chapter.draft, chapter.draft]})

        if chapter.draft:
            story.words -= chapter.words
        else:
            story.words += chapter.words

        if not story.draft and story.published and not chapter.first_published_at:
            chapter.first_published_at = datetime.utcnow()
            later(current_app.tasks['notify_story_chapters'].delay, [chapter.id], user.id if user else None)

        # Это необходимо, пока архивы для скачивания рассказа обновляются по этой дате
        story.updated = datetime.utcnow()

        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)

    def viewed(self, user):
        if not user.is_authenticated:
            return

        from mini_fiction.models import StoryView

        chapter = self.model
        story = chapter.story

        story_view = view = StoryView.select(lambda x: x.story == story and x.author == user).first()
        view = StoryView.get(story=story, chapter=chapter, author=user)

        if not view:
            view = StoryView(
                story=story,
                chapter=chapter,
                author=user,
            )
            chapter.views += 1
            if not story_view:
                story.views += 1
        return view

    def add_chapters_to_search(self, chapters):
        if current_app.config['SPHINX_DISABLED']:
            return
        chapters = [{
            'id': chapter.id,
            'title': chapter.title,
            'notes': chapter.notes,
            'text': chapter.text,
            'story_id': chapter.story.id,
            'published': chapter.story_published and not chapter.draft,
            'first_published_at': int(((chapter.first_published_at or chapter.date) - datetime(1970, 1, 1, 0, 0, 0)).total_seconds()),
        } for chapter in chapters]

        with current_app.sphinx as sphinx:
            sphinx.add('chapters', chapters)

    def delete_chapters_from_search(self, chapter_ids):
        if current_app.config['SPHINX_DISABLED']:
            return
        with current_app.sphinx as sphinx:
            sphinx.delete('chapters', id__in=chapter_ids)

    def search_add(self):
        chapter = self.model
        self.add_chapters_to_search((chapter,))
        chapter.story.bl.search_update(('words',))

    def search_update(self):
        self.search_add()

    def search_delete(self):
        chapter = self.model
        self.delete_chapters_from_search((chapter.id,))
        chapter.story.bl.search_update(('words',))

    def search(self, query, limit, only_published=True):
        if current_app.config['SPHINX_DISABLED']:
            return {}, []
        sphinx_filters = {}
        if only_published:
            sphinx_filters['published'] = 1

        with current_app.sphinx as sphinx:
            raw_result = sphinx.search(
                'chapters',
                query,
                weights=current_app.config['SPHINX_CONFIG']['weights_chapters'],
                options=current_app.config['SPHINX_CONFIG']['select_options'],
                limit=limit,
                **sphinx_filters
            )

            ids = [x['id'] for x in raw_result['matches']]
            dresult = {x.id: x for x in self.model.select(lambda x: x.id in ids).prefetch(self.model.story)}
            result = []
            for i in ids:
                if i not in dresult:
                    continue
                excerpt = sphinx.call_snippets('chapters', dresult[i].text, query, **current_app.config['SPHINX_CONFIG']['excerpts_opts'])
                result.append((dresult[i], excerpt[0] if excerpt else ''))

        return raw_result, result
