#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import json
import random
import ipaddress
from hashlib import md5
from datetime import datetime, timedelta

import lxml.html
import lxml.etree
from pony import orm
from flask import Markup, current_app

from mini_fiction.bl.utils import BaseBL
from mini_fiction.bl.commentable import Commentable
from mini_fiction.utils.misc import words_count, call_after_request as later
from mini_fiction.utils.misc import normalize_text_for_search_index, normalize_text_for_search_query
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
        2: "words DESC",
        3: "vote_value DESC",
        4: "comments_count DESC",
        5: "RAND()",
    }

    _contributors = None

    def create(self, authors, data):
        from mini_fiction.models import Category, Character, Classifier, StoryContributor

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
            freezed=data['status'] == 'freezed',
            finished=data['status'] == 'finished',
            source_link=data['source_link'],
            source_title=data['source_title'],
            notes=data['notes'],
            draft=True,
            approved=approved,
            vote_total=0,
            vote_value=current_app.story_voting.get_default_vote_value() if current_app.story_voting else 0,
            vote_extra=current_app.story_voting.get_default_vote_extra() if current_app.story_voting else '{}',
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
                visible=True,
            ).flush()

        story.bl.subscribe_to_comments(authors[0], email=True, tracker=True)
        story.bl.subscribe_to_local_comments(authors[0], email=True, tracker=True)

        current_app.cache.delete('index_updated_chapters')

        later(current_app.tasks['sphinx_update_story'].delay, story.id, None)
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
        changed_sphinx_fields = set()

        if 'status' in data:
            new_freezed = data['status'] == 'freezed'
            new_finished = data['status'] == 'finished'
            if story.freezed != new_freezed or story.finished != new_finished:
                edited_data['freezed'] = [story.freezed, new_freezed]
                story.freezed = edited_data['freezed'][1]
                edited_data['finished'] = [story.finished, new_finished]
                story.finished = edited_data['finished'][1]
                changed_sphinx_fields.add('freezed')
                changed_sphinx_fields.add('finished')

        for key in ('title', 'summary', 'notes', 'original'):
            if key in data and getattr(story, key) != data[key]:
                edited_data[key] = [getattr(story, key), data[key]]
                setattr(story, key, data[key])
                changed_sphinx_fields.add(key)

        for key in ('source_link', 'source_title'):
            if key in data and getattr(story, key) != data[key]:
                edited_data[key] = [getattr(story, key), data[key]]
                setattr(story, key, data[key])

        if 'rating' in data and story.rating.id != data['rating']:
            edited_data['rating'] = [story.rating.id, data['rating']]
            story.rating = Rating.get(id=data['rating'])
            changed_sphinx_fields.add('rating_id')

        # TODO: refactor
        if 'categories' in data:
            old_value = sorted(x.id for x in story.categories)
            new_value = sorted(data['categories'])
            if set(old_value) != set(new_value):
                edited_data['categories'] = [old_value, new_value]
                story.categories.clear()
                story.categories.add(Category.select(lambda x: x.id in data['categories'])[:])
                changed_sphinx_fields.add('category')

        if 'characters' in data:
            old_value = sorted(x.id for x in story.characters)
            new_value = sorted(data['characters'])
            if set(old_value) != set(new_value):
                edited_data['characters'] = [old_value, new_value]
                story.characters.clear()
                story.characters.add(Character.select(lambda x: x.id in data['characters'])[:])
                changed_sphinx_fields.add('character')

        if 'classifications' in data:
            old_value = sorted(x.id for x in story.classifications)
            new_value = sorted(data['classifications'])
            if set(old_value) != set(new_value):
                edited_data['classifications'] = [old_value, new_value]
                story.classifications.clear()
                story.classifications.add(Classifier.select(lambda x: x.id in data['classifications'])[:])
                changed_sphinx_fields.add('classifier')

        if edited_data:
            story.updated = datetime.utcnow()
            current_app.cache.delete('index_updated_chapters')
            current_app.cache.delete('index_comments_html')

        if editor and edited_data:
            self.edit_log(editor, edited_data)

        if old_published != story.published:
            for c in story.chapters:
                c.story_published = story.published

        if changed_sphinx_fields:
            later(current_app.tasks['sphinx_update_story'].delay, story.id, tuple(changed_sphinx_fields))
        return story

    def approve(self, user, approved):
        # TODO: с publish() очень много общего, можно вынести общее в отдельную функцию
        story = self.model
        tm = datetime.utcnow()

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
            story.last_author_notification_at = tm
            story.last_staff_notification_at = None
            later(current_app.tasks['notify_story_publish_draft'].delay, story.id, user.id, not story.published)

        changed_sphinx_fields = set()

        if old_approved != story.approved:
            changed_sphinx_fields.add('approved')

        if old_published != story.published:
            if story.published and not story.first_published_at:
                story.bl.first_publish(tm=tm, caused_by_user=user)
                changed_sphinx_fields.add('first_published_at')

            published_chapter_ids = []
            for c in sorted(story.chapters, key=lambda c: c.order):
                c.story_published = story.published
                if story.published and not c.draft and not c.first_published_at:
                    c.bl.first_publish(tm=tm, notify=False, caused_by_user=user)  # Уведомления разошлём сами чуть ниже
                    published_chapter_ids.append(c.id)

            if published_chapter_ids:
                later(current_app.tasks['notify_story_chapters'].delay, published_chapter_ids, user.id if user else None)

            for c in story.comments:  # TODO: update StoryComment where story = story.id
                c.story_published = story.published

            current_app.cache.delete('index_updated_chapters')
            current_app.cache.delete('index_comments_html')

        if changed_sphinx_fields:
            later(current_app.tasks['sphinx_update_story'].delay, story.id, tuple(changed_sphinx_fields))

    def publish(self, user, published):
        # TODO: с approve() очень много общего, можно вынести общее в отдельную функцию
        story = self.model
        tm = datetime.utcnow()
        old_published = story.published  # not draft and approved
        old_draft = story.draft

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
                if not user or not user.is_staff:
                    story.last_author_notification_at = None
                later(current_app.tasks['notify_story_pubrequest'].delay, story.id, user.id)

            # Уведомление автора о скрытии рассказа модератором, если:
            # 1) Это и правда модератор
            notify_draft = user and user.is_staff
            # 2) Рассказ отправлялся на публикацию или был опубликован
            # (FIXME: удаление одобрение отправляет такое же уведомление, получается дубликат)
            notify_draft = notify_draft and (not old_draft and story.draft)
            # 3) Про почту: с момента предыдущего уведомления прошло достаточно времени
            fast = not (
                not story.last_author_notification_at or
                story.last_author_notification_at + timedelta(seconds=current_app.config['STORY_NOTIFICATIONS_INTERVAL']) < datetime.utcnow()
            )

            if notify_draft:
                story.last_author_notification_at = datetime.utcnow()
                story.last_staff_notification_at = None
                later(current_app.tasks['notify_story_publish_draft'].delay, story.id, user.id, not story.published, fast=fast)

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
            changed_sphinx_fields = {'draft',}
            if old_published != story.published:
                if story.published and not story.first_published_at:
                    story.bl.first_publish(tm=tm, caused_by_user=user)
                    changed_sphinx_fields.add('first_published_at')

                published_chapter_ids = []
                for c in sorted(story.chapters, key=lambda c: c.order):
                    c.story_published = story.published
                    if story.published and not c.draft and not c.first_published_at:
                        c.bl.first_publish(tm=tm, notify=False, caused_by_user=user)  # Уведомления разошлём сами чуть ниже
                        published_chapter_ids.append(c.id)
                    later(current_app.tasks['sphinx_update_chapter'].delay, c.id)

                if published_chapter_ids:
                    later(current_app.tasks['notify_story_chapters'].delay, published_chapter_ids, user.id if user else None)

                for c in story.comments:
                    c.story_published = story.published

                current_app.cache.delete('index_updated_chapters')
                current_app.cache.delete('index_comments_html')

            later(current_app.tasks['sphinx_update_story'].delay, story.id, tuple(changed_sphinx_fields))

            return True

        return False

    def first_publish(self, tm=None, caused_by_user=None):
        # Метод для действий при первой публикации рассказа

        story = self.model
        assert story.first_published_at is None

        if tm is None:
            tm = datetime.utcnow()

        story.first_published_at = tm

        later(current_app.tasks['notify_author_story'].delay, story.id, caused_by_user.id if caused_by_user else None)

        # Уведомляем поисковых роботов о новом рассказе с помощью Sitemap
        later(current_app.tasks['sitemap_ping_story'].delay, story.id)

    def publish_all_chapters(self, user=None):
        story = self.model
        published_chapter_ids = []
        tm = datetime.utcnow()

        for c in sorted(story.chapters, key=lambda x: x.order):
            if not c.draft:
                continue
            c.draft = False
            c.bl.edit_log(user, 'edit', {'draft': [True, False]})
            story.words += c.words
            later(current_app.tasks['sphinx_update_chapter'].delay, c.id)
            if story.published and not c.first_published_at:
                c.bl.first_publish(tm=tm, notify=False, caused_by_user=user)  # Уведомления разошлём сами чуть ниже
                published_chapter_ids.append(c.id)

        later(current_app.tasks['sphinx_update_story'].delay, story.id, ('words',))

        if published_chapter_ids:
            later(current_app.tasks['notify_story_chapters'].delay, published_chapter_ids, user.id if user else None)
            current_app.cache.delete('index_updated_chapters')

    def delete(self, user=None):
        from mini_fiction.models import Chapter, StoryComment, StoryCommentVote, StoryCommentEdit
        from mini_fiction.models import StoryLocalComment, StoryLocalCommentEdit, Subscription, Notification

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
            lambda x: x.type in ('story_chapter', 'story_comment', 'story_lcomment') and x.target_id == story_id
        ).delete(bulk=True)

        # Неявная связь с уведомлениями
        Notification.select(
            lambda x: x.type in ('story_publish', 'story_draft', 'author_story') and x.target_id == story_id
        ).delete(bulk=True)

        # Неявная связь с уведомлениями о новых главах
        chapter_ids = orm.select(x.id for x in Chapter if x.story.id == story_id)
        Notification.select(
            lambda x: x.type in ('story_chapter',) and x.target_id in chapter_ids
        ).delete(bulk=True)

        comment_ids = orm.select(x.id for x in StoryComment if x.story.id == story_id)
        Notification.select(
            lambda x: x.type in ('story_reply', 'story_comment') and x.target_id in comment_ids
        ).delete(bulk=True)
        # Да-да, поне надо помогать
        orm.select(c for c in StoryCommentVote if c.comment in story.comments).delete(bulk=True)
        orm.select(c for c in StoryCommentEdit if c.comment in story.comments).delete(bulk=True)
        story.comments.select().order_by(StoryComment.id.desc()).delete(bulk=False)  # поня не может bulk

        if local_thread_id is not None:
            local_comment_ids = orm.select(x.id for x in StoryLocalComment if x.local.id == local_thread_id)[:]
            Notification.select(
                lambda x: x.type in ('story_lreply', 'story_lcomment') and x.target_id in local_comment_ids
            ).delete(bulk=True)
            orm.select(c for c in StoryLocalCommentEdit if c.comment.id in local_comment_ids).delete(bulk=True)
            story.local.comments.select().order_by(StoryLocalComment.id.desc()).delete(bulk=False)  # не может в bulk, ага

        # Не помню почему, но почему-то там Optional
        story.story_views_set.select().delete(bulk=True)
        story.activity.select().delete(bulk=True)
        story.votes.select().delete(bulk=True)

        # Остальные связи Pony ORM осилит
        story.delete()
        orm.flush()
        current_app.cache.delete('index_updated_chapters')

    def get_activity(self, user):
        from mini_fiction.models import Activity

        if not user.is_authenticated:
            return
        story = self.model
        # Если по каким-то причинам сайт лаганул и насоздавал активитей, то используем
        # select/first вместо get, чтоб ошибки 500 не было
        return Activity.select(lambda x: x.story == story and x.author == user).first()

    def viewed(self, user):
        if not user.is_authenticated:
            return

        from mini_fiction.models import Activity

        story = self.model
        last_comment = self.select_comments().order_by('-c.id').first()
        data = {
            'last_views': story.views,
            'last_comments': story.comments_count,
            'last_comment_id': last_comment.id if last_comment else 0,
        }

        acts = Activity.select(lambda x: x.story == story and x.author == user)[:]
        if acts:
            for act in acts[1:]:
                # Если по каким-то причинам сайт лаганул и насоздавал активитей, то удаляем лишнее
                act.delete()
            act = acts[0]
        else:
            act = None
        del acts

        if not act:
            act = Activity(story=story, author=user, **data)
        else:
            for k, v in data.items():
                setattr(act, k, v)
        return act

    def vote(self, user, value, ip):
        from mini_fiction.models import Vote

        story = self.model
        if not current_app.story_voting:
            raise ValueError('Оценивание рассказов недоступно')
        if self.is_author(user):
            raise ValueError('Нельзя голосовать за свой рассказ')
        if not self.can_vote(user):
            raise ValueError('Вы не можете голосовать за этот рассказ')
        if not current_app.story_voting.validate_value(value):
            raise ValueError('Неверное значение')

        ip = ipaddress.ip_address(ip).exploded

        vote = Vote.select(lambda x: x.author == user and x.story == story).for_update().first()
        if not vote:
            vote = Vote(
                author=user,
                story=story,
                vote_value=value,
                ip=ip,
                revoked_at=None,
            )
        elif value != vote.vote_value:
            vote.vote_value = value
            vote.ip = ip
            vote.updated = datetime.utcnow()
        vote.flush()
        self.update_rating()
        return vote

    def update_rating(self):
        if not current_app.story_voting:
            return
        story = self.model
        current_app.story_voting.update_rating(story)
        story.flush()
        later(current_app.tasks['sphinx_update_story'].delay, story.id, ('vote_total', 'vote_value'))

    def vote_view_html(self, user=None, full=False):
        if not current_app.story_voting:
            return ''
        return current_app.story_voting.vote_view_html(self.model, user=user, full=full)

    def vote_area_1_html(self, user=None, user_vote=None):
        if not current_app.story_voting:
            return ''
        return current_app.story_voting.vote_area_1_html(self.model, user=user, user_vote=user_vote)

    def vote_area_2_html(self, user=None, user_vote=None):
        if not current_app.story_voting:
            return ''
        return current_app.story_voting.vote_area_2_html(self.model, user=user, user_vote=user_vote)

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

    def edit_contributors(self, editor, contributors):
        from mini_fiction.models import Author, StoryContributor

        # Собираем старых участников для записи в лог изменений
        old_contributors = [{
            'user': x.user.id,
            'visible': x.visible,
            'is_editor': x.is_editor,
            'is_author': x.is_author,
        } for x in self.get_contributors()]

        # {user_id: StoryContributor object}
        objs = {x.user.id: x for x in self.get_contributors()}

        # Собираем обновления участников
        for user_id, acc in contributors.items():
            user = Author.get(id=user_id)
            if not user:
                raise ValueError('User not found')

            # None означает, что доступ этому участнику нужно удалить
            if acc is None:
                if user_id in objs:
                    objs.pop(user_id).delete()
                continue

            # Если не None, то создаём или обновляем права доступа
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

        # Собираем новых участников для записи в лог изменений
        new_contributors = [{
            'user': x.user.id,
            'visible': x.visible,
            'is_editor': x.is_editor,
            'is_author': x.is_author,
        } for x in self.get_contributors()]

        # Если разница есть, то записываем в лог
        if old_contributors != new_contributors:
            self.edit_log(editor, {'contributors': [old_contributors, new_contributors]})

    # access control

    def get_contributors(self):
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

        # Модераторы имеют доступ всегда
        if user and user.is_staff:
            return True

        # Авторы, очевидно, тоже должны иметь доступ всегда
        # Опубликованный рассказ тоже всегда доступен всем
        if story.published or self.is_contributor(user):
            return True

        # Остальное означает доступ по прямой ссылке (рассказ скрыт со всех
        # публичных выборок) и зависит от настроек
        direct_access = story.direct_access or current_app.config['STORY_DIRECT_ACCESS']

        if direct_access == 'all':
            # Доступ всегда, даже черновику
            allowed = True
        elif direct_access == 'none':
            # Доступ никогда, если не опубликован
            allowed = False
        elif direct_access in ('nodraft', 'anodraft'):
            # Доступ только если не в черновиках (в том числе
            # для неопубликованного на модерации; полезно для песочниц)
            allowed = not story.draft
        else:
            # Админ глупенький
            raise ValueError('Incorrect settings: STORY_DIRECT_ACCESS can be all, none, nodraft or anodraft (got {!r})'.format(direct_access))

        if not allowed:
            return False

        # anodraft означает доступ по прямой ссылке в том числе гостям
        if direct_access == 'anodraft':
            return True

        # Если не anodraft, то доступ гостей проверяется по настройкам
        if (not user or not user.is_authenticated) and not current_app.config['STORY_DIRECT_ACCESS_FOR_GUEST']:
            return False

        return True

    def can_vote(self, user):
        story = self.model
        if user and user.is_staff:
            return True
        if not user or not user.is_authenticated or not story.published or self.is_author(user):
            return False
        return self.has_access(user)

    # search

    def add_stories_to_search(self, stories, with_chapters=True):
        if current_app.config['SPHINX_DISABLED']:
            return
        sphinx_stories = []
        for story in stories:
            data = {
                'id': story.id,
                'title': normalize_text_for_search_index(story.title, html=False),
                'summary': normalize_text_for_search_index(story.summary, html=True),
                'notes': normalize_text_for_search_index(story.notes, html=True),
                'match_author': ' '.join(x.username for x in story.authors),

                'first_published_at': int(((story.first_published_at or story.date) - datetime(1970, 1, 1, 0, 0, 0)).total_seconds()),
                'words': story.words,
            }
            data.update(story.bl.sphinx_get_common_fields())
            sphinx_stories.append(data)

        with current_app.sphinx as sphinx:
            sphinx.add('stories', sphinx_stories)

        if with_chapters:
            from mini_fiction.models import Chapter
            chapters = sum([list(x.chapters) for x in stories], [])
            Chapter.bl.add_chapters_to_search(chapters)

    def delete_stories_from_search(self, story_ids):
        if current_app.config['SPHINX_DISABLED']:
            return
        with current_app.sphinx as sphinx:
            sphinx.delete('stories', id__in=story_ids)
        with current_app.sphinx as sphinx:
            sphinx.delete('chapters', story_id__in=story_ids)

    def search_add(self, with_chapters=True):
        self.add_stories_to_search((self.model,), with_chapters=with_chapters)

    def search_update(self, update_fields=(), with_chapters=True):
        if current_app.config['SPHINX_DISABLED']:
            return
        story = self.model

        f = set(update_fields)

        # Изменённые поля, общие и для рассказа, и для его глав
        common_fields = self.sphinx_get_common_fields(f)
        # Изменённые поля конкретно рассказа
        story_fields = common_fields.copy()

        if 'first_published_at' in f:
            # first_published_at изменяется только один раз и одновременно у рассказов и у глав
            # Поэтому смело пихаем в common_fields
            common_fields['first_published_at'] = int(((story.first_published_at or story.date) - datetime(1970, 1, 1, 0, 0, 0)).total_seconds())
            story_fields['first_published_at'] = common_fields['first_published_at']

        if 'words' in f:
            story_fields['words'] = story.words

        if f - set(story_fields):
            # Есть неучтённые поля — для них оптимизаций нет, тупо переиндексируем всё
            self.search_add(with_chapters=False)
        else:
            with current_app.sphinx as sphinx:
                sphinx.update('stories', fields=story_fields, id=story.id)

        if with_chapters and common_fields and list(story.chapters):
            with current_app.sphinx as sphinx:
                sphinx.update('chapters', fields=common_fields, id__in=[x.id for x in story.chapters])

    def search_delete(self):
        self.delete_stories_from_search((self.model.id,))

    def sphinx_get_common_fields(self, fields=None):
        story = self.model
        common_fields = {}

        f = set(fields) if fields is not None else None

        # TODO: rename vote_total to vote_count
        for field in (
            'vote_total', 'vote_value', 'comments_count',
            'finished', 'original', 'freezed', 'draft', 'approved',
        ):
            if f is None or field in f:
                common_fields[field] = getattr(story, field)

        if f is None or 'rating_id' in f:
            common_fields['rating_id'] = story.rating.id

        if f is None or 'character' in f:
            common_fields['character'] = [x.id for x in story.characters]  # TODO: check performance
        if f is None or 'category' in f:
            common_fields['category'] = [x.id for x in story.categories]
        if f is None or 'classifier' in f:
            common_fields['classifier'] = [x.id for x in story.classifications]
        if f is None or 'author' in f:
            common_fields['author'] = [x.id for x in story.authors]

        return common_fields

    def search(self, query, limit, sort_by=0, only_published=True, extended_syntax=True, **filters):
        if current_app.config['SPHINX_DISABLED']:
            return {}, []

        if sort_by not in self.sort_types:
            sort_by = 0

        sphinx_filters = {}
        if only_published:
            sphinx_filters['draft'] = 0
            sphinx_filters['approved'] = 1

        query = normalize_text_for_search_query(query)

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
            sphinx_filters['words__gte'] = int(filters['min_words'])
        if filters.get('max_words') is not None:
            sphinx_filters['words__lte'] = int(filters['max_words'])

        if filters.get('min_vote_total') is not None:
            sphinx_filters['vote_total__gte'] = int(filters['min_vote_total'])
        if filters.get('max_vote_total') is not None:
            sphinx_filters['vote_total__lte'] = int(filters['max_vote_total'])

        if filters.get('min_vote_value') is not None:
            sphinx_filters['vote_value__gte'] = int(filters['min_vote_value'])
        if filters.get('max_vote_value') is not None:
            sphinx_filters['vote_value__lte'] = int(filters['max_vote_value'])

        with current_app.sphinx as sphinx:
            raw_result = sphinx.search(
                'stories',
                query,
                weights=current_app.config['SPHINX_CONFIG']['weights_stories'],
                options=current_app.config['SPHINX_CONFIG']['select_options'],
                limit=limit,
                sort_by=self.sort_types[sort_by],
                extended_syntax=extended_syntax,
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

    def access_for_commenting_by(self, author=None):
        from mini_fiction.models import StoryComment
        return StoryComment.bl.access_for_commenting_by(self.model, author)

    def create_comment(self, author, ip, data):
        from mini_fiction.models import StoryComment
        return StoryComment.bl.create(self.model, author, ip, data)

    def select_comments(self):
        from mini_fiction.models import StoryComment
        return orm.select(c for c in StoryComment if c.story == self.model)

    def select_comment_ids(self):
        from mini_fiction.models import StoryComment
        return orm.select(c.id for c in StoryComment if c.story == self.model)

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

        act = self.get_activity(user)
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
        return None

    # misc

    def get_random(self, count=10):
        # это быстрее, чем RAND() в MySQL
        from mini_fiction.models import Story

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

    def access_for_commenting_by(self, author=None):
        from mini_fiction.models import StoryLocalComment
        return StoryLocalComment.bl.access_for_commenting_by(self.model, author)

    def create_comment(self, author, ip, data):
        from mini_fiction.models import StoryLocalComment
        return StoryLocalComment.bl.create(self.model, author, ip, data)

    def select_comments(self):
        from mini_fiction.models import StoryLocalComment
        return orm.select(c for c in StoryLocalComment if c.local == self.model)

    def select_comment_ids(self):
        from mini_fiction.models import StoryLocalComment
        return orm.select(c.id for c in StoryLocalComment if c.local == self.model)

    def comment2html(self, text):
        from mini_fiction.models import StoryLocalComment
        return StoryLocalComment.bl.text2html(text)


class ChapterBL(BaseBL):
    sort_types = {
        0: "weight() DESC, first_published_at DESC",
        1: "first_published_at DESC",
        2: "words DESC",
        3: "vote_value DESC",
        4: "comments_count DESC",
        5: "RAND()",
    }

    def create(self, story, editor, data):
        from mini_fiction.models import Chapter
        from mini_fiction.validation.utils import safe_string_coerce, safe_string_multiline_coerce

        new_order = orm.select(orm.max(x.order) for x in Chapter if x.story == story).first()

        text = safe_string_multiline_coerce(data['text']).strip()
        assert '\r' not in text

        chapter = self.model(
            story=story,
            title=safe_string_coerce(data['title']).strip(),
            notes=safe_string_multiline_coerce(data['notes']).strip(),
            text=text,
            text_md5=md5(text.encode('utf-8')).hexdigest(),
            draft=True,
            story_published=story.published,
        )
        chapter.order = (new_order or 0) + 1

        self.update_words_count(chapter)
        chapter.flush()
        chapter.bl.edit_log(editor, 'add', {}, text_md5=chapter.text_md5)
        story.updated = datetime.utcnow()
        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        # current_app.cache.delete('index_updated_chapters') не нужен, если draft=True
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
        from mini_fiction.validation.utils import safe_string_coerce, safe_string_multiline_coerce

        # TODO: move validation to Cerberus
        data = dict(data)
        if 'title' in data:
            data['title'] = safe_string_coerce(data['title']).strip()
        if 'notes' in data:
            data['notes'] = safe_string_multiline_coerce(data['notes']).strip()
        if 'text' in data:
            data['text'] = safe_string_multiline_coerce(data['text']).strip()
            assert '\r' not in data['text']

        chapter = self.model
        edited_data = {}
        chapter_text_diff = None

        if 'title' in data and data['title'] != chapter.title:
            edited_data['title'] = [chapter.title, data['title']]
            chapter.title = data['title']

        if 'notes' in data and data['notes'] != chapter.notes:
            edited_data['notes'] = [chapter.notes, data['notes']]
            chapter.notes = data['notes']

        text = data.get('text')
        if text is not None and text != chapter.text:
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
            self.update_words_count(chapter)

        if edited_data or chapter_text_diff:
            chapter.updated = datetime.utcnow()
            chapter.story.updated = datetime.utcnow()
            chapter.bl.edit_log(editor, 'edit', edited_data, chapter_text_diff=chapter_text_diff, text_md5=chapter.text_md5)

        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        return chapter

    def update_words_count(self, chapter, update_story_words=True):
        old_words = chapter.words
        new_words = words_count(chapter.text, html=True)
        if new_words != chapter.words:
            chapter.words = new_words
            if update_story_words and not chapter.draft:
                story = chapter.story
                story.words = story.words - old_words + new_words
        return old_words, new_words

    def delete(self, editor):
        from mini_fiction.models import Chapter

        chapter = self.model
        story = chapter.story
        if not chapter.draft:
            story.words = story.words - chapter.words
        later(current_app.tasks['sphinx_delete_chapter'].delay, story.id, chapter.id)

        old_order = chapter.order
        chapter.bl.edit_log(editor, 'delete', {})

        # Помогаем поне удалять связи
        for x in chapter.edit_log:
            x.chapter = None
        chapter.chapter_views_set.select().delete(bulk=True)

        chapter.delete()
        chapter.flush()

        for c in Chapter.select(lambda x: x.story == story and x.order > old_order).order_by('x.order'):
            c.order = c.order - 1
            c.flush()

        story.updated = datetime.utcnow()
        current_app.cache.delete('index_updated_chapters')

    def notes2html(self, notes):
        from mini_fiction.validation.utils import safe_string_multiline_coerce

        notes = safe_string_multiline_coerce(notes or '').strip()
        if not notes:
            return Markup('')

        try:
            doc = filter_html(notes)
            return Markup(html_doc_to_string(doc))
        except Exception:
            import sys
            import traceback
            print(datetime.now().strftime('[%Y-%m-%d %H:%M:%S]'), "filter_html_notes failed", file=sys.stderr)
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
        from mini_fiction.validation.utils import safe_string_multiline_coerce

        safe_text = safe_string_multiline_coerce(text or '').strip()
        if not safe_text:
            return Markup('')

        try:
            if start is not None and end is not None and start < end and start >= 0 and start < len(text) - 1:
                # FIXME: нельзя просто так взять и накатить safe_string_multiline_coerce, ибо start и end сместятся
                doc = self.filter_text_for_preview(text, start, end)
            else:
                doc = self.filter_text(safe_text)
            doc = footnotes_to_html(doc)
            return Markup(html_doc_to_string(doc))
        except Exception:
            import traceback
            if current_app.config['DEBUG']:
                return traceback.format_exc()
            print(datetime.now().strftime('[%Y-%m-%d %H:%M:%S]'), "story text2html failed", file=sys.stderr)
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
        tm = datetime.utcnow()
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
            chapter.bl.first_publish(tm=tm, notify=True, caused_by_user=user)

        # Это необходимо, пока архивы для скачивания рассказа обновляются по этой дате
        story.updated = tm

        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        current_app.cache.delete('index_updated_chapters')

    def first_publish(self, tm=None, notify=True, caused_by_user=None):
        # Метод для действий при первой публикации главы

        chapter = self.model
        assert chapter.first_published_at is None
        assert chapter.story.first_published_at is not None

        if tm is None:
            tm = datetime.utcnow()

        chapter.first_published_at = tm

        # Уведомление пользователей о появлении новой главы. Его можно
        # отключить для того, чтобы при публикации нескольких глав
        # одновременно уведомить обо всех одним письмом (см. StoryBL)
        if notify:
            later(current_app.tasks['notify_story_chapters'].delay, [chapter.id], caused_by_user.id if caused_by_user else None)

    def is_viewed_by(self, user):
        from mini_fiction.models import StoryView

        if not user or not user.is_authenticated:
            return None

        chapter = self.model
        story = chapter.story

        # Так надо, чтобы поня закэшировала SQL-запрос и списки рассказов не тормозили
        viewed_chapters = StoryView.select(lambda x: x.author.id == user.id and x.story == story)
        viewed_chapters = {x.chapter.id: x.date for x in viewed_chapters if x.chapter}
        return viewed_chapters.get(chapter.id)

    def viewed(self, user):
        if not user.is_authenticated:
            return

        from mini_fiction.models import StoryView

        chapter = self.model
        story = chapter.story

        story_view = StoryView.select(lambda x: x.story == story and x.author == user).first()
        # Из-за всяких легаси у одной главы от одного юзера может быть несколько просмотров,
        # поэтому select/first вместо get
        view = StoryView.select(lambda x: x.story == story and x.chapter == chapter and x.author == user).first()

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

    # search

    def add_chapters_to_search(self, chapters, update_story_words=True):
        if current_app.config['SPHINX_DISABLED']:
            return

        sphinx_chapters = []
        for chapter in chapters:
            data = {
                'id': chapter.id,

                'title': normalize_text_for_search_index(chapter.title, html=False),
                'notes': normalize_text_for_search_index(chapter.notes, html=True),
                'text': normalize_text_for_search_index(chapter.text, html=True),

                'story_id': chapter.story.id,
                'first_published_at': int(((chapter.first_published_at or chapter.date) - datetime(1970, 1, 1, 0, 0, 0)).total_seconds()),
                'words': chapter.words,

                'chapter_draft': chapter.draft,
            }
            data.update(chapter.story.bl.sphinx_get_common_fields())
            sphinx_chapters.append(data)

        with current_app.sphinx as sphinx:
            sphinx.add('chapters', sphinx_chapters)

        if update_story_words:
            stories = {}
            for chapter in chapters:
                stories[chapter.story.id] = chapter.story
            with current_app.sphinx as sphinx:
                for story in stories.values():
                    story.bl.search_update(('words',))

    def delete_chapters_from_search(self, story_ids, chapter_ids, update_story_words=True):
        if current_app.config['SPHINX_DISABLED']:
            return
        with current_app.sphinx as sphinx:
            sphinx.delete('chapters', id__in=chapter_ids)

        if story_ids and update_story_words:
            from mini_fiction.models import Story
            stories = Story.select(lambda x: x.id in story_ids)
            for s in stories:
                s.bl.search_update(update_fields=('words',))

    def search_add(self, update_story_words=True):
        self.add_chapters_to_search((self.model,), update_story_words=update_story_words)

    def search_update(self, update_story_words=True):
        self.search_add(update_story_words=update_story_words)

    def search_delete(self, update_story_words=True):
        self.delete_chapters_from_search((self.model.story.id), (self.model.id,), update_story_words=update_story_words)

    def search(self, query, limit, sort_by=0, only_published=True, extended_syntax=True, **filters):
        if current_app.config['SPHINX_DISABLED']:
            return {}, []

        if sort_by not in self.sort_types:
            sort_by = 0

        query = normalize_text_for_search_query(query)

        sphinx_filters = {}
        if only_published:
            sphinx_filters['chapter_draft'] = 0
            sphinx_filters['draft'] = 0
            sphinx_filters['approved'] = 1

        for ifilter in ('original', 'finished', 'freezed', 'character', 'classifier', 'category', 'rating_id'):
            if filters.get(ifilter):
                sphinx_filters[ifilter + '__in'] = [int(x) for x in filters[ifilter]]

        if filters.get('excluded_categories'):
            sphinx_filters['category__not_in'] = [int(x) for x in filters['excluded_categories']]

        if filters.get('min_words') is not None:
            sphinx_filters['words__gte'] = int(filters['min_words'])
        if filters.get('max_words') is not None:
            sphinx_filters['words__lte'] = int(filters['max_words'])

        if filters.get('min_vote_total') is not None:
            sphinx_filters['vote_total__gte'] = int(filters['min_vote_total'])
        if filters.get('max_vote_total') is not None:
            sphinx_filters['vote_total__lte'] = int(filters['max_vote_total'])

        if filters.get('min_vote_value') is not None:
            sphinx_filters['vote_value__gte'] = int(filters['min_vote_value'])
        if filters.get('max_vote_value') is not None:
            sphinx_filters['vote_value__lte'] = int(filters['max_vote_value'])

        with current_app.sphinx as sphinx:
            raw_result = sphinx.search(
                'chapters',
                query,
                weights=current_app.config['SPHINX_CONFIG']['weights_chapters'],
                options=current_app.config['SPHINX_CONFIG']['select_options'],
                limit=limit,
                sort_by=self.sort_types[sort_by],
                extended_syntax=extended_syntax,
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
