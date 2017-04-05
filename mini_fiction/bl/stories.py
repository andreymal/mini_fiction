#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import json
import random
import ipaddress
from datetime import datetime
from statistics import mean, pstdev

from pony import orm
from flask import Markup, current_app

from mini_fiction.bl.utils import BaseBL
from mini_fiction.bl.commentable import Commentable
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.validation import Validator
from mini_fiction.validation.stories import STORY


class StoryBL(BaseBL, Commentable):
    sort_types = {
        0: "weight() DESC, id DESC",
        1: "id DESC",
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

        if old_published != story.published:
            if story.published and not story.first_published_at:
                story.first_published_at = datetime.utcnow()
            later(current_app.tasks['sphinx_update_story'].delay, story.id, ('approved',))
            for c in story.chapters:
                c.story_published = story.published  # TODO: update Chapter where story = story.id
                if story.published and not c.draft and not c.first_published_at:
                    c.first_published_at = datetime.utcnow()
                later(current_app.tasks['sphinx_update_chapter'].delay, c.id)
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

            if old_published != story.published:
                if story.published and not story.first_published_at:
                    story.first_published_at = datetime.utcnow()
                later(current_app.tasks['sphinx_update_story'].delay, story.id, ('draft',))
                for c in sorted(story.chapters, key=lambda c: c.order):
                    c.story_published = story.published
                    if story.published and not c.draft and not c.first_published_at:
                        c.first_published_at = datetime.utcnow()
                    later(current_app.tasks['sphinx_update_chapter'].delay, c.id)
                for c in story.comments:
                    c.story_published = story.published
            return True

        return False

    def publish_all_chapters(self):
        story = self.model
        for c in sorted(story.chapters, key=lambda x: x.order):
            if not c.draft:
                continue
            story.words += c.words
            c.draft = False
            later(current_app.tasks['sphinx_update_chapter'].delay, c.id)
            if story.published and not c.first_published_at:
                c.first_published_at = datetime.utcnow()

    def delete(self):
        story = self.model
        later(current_app.tasks['sphinx_delete_story'].delay, story.id)
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
            vote.flush()
            self._update_rating()
        elif value != vote.vote_value:
            vote.vote_value = value
            vote.ip = ip
            vote.flush()
            self._update_rating()

        return vote

    def _update_rating(self):
        from mini_fiction.models import Vote

        story = self.model
        votes = orm.select(x.vote_value for x in Vote if x.story == story)[:]
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

    def select_by_author(self, author, queryset=None):
        from mini_fiction.models import StoryContributor

        if not queryset:
            queryset = self.model.select()
        return queryset.filter(lambda x: x in orm.select(y.story for y in StoryContributor if y.user == author and y.is_author))

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
                    is_editor=acc['is_editor'],
                    is_author=acc['is_author'],
                )
                objs[user_id].flush()
            else:
                objs[user_id].is_editor = acc['is_editor']
                objs[user_id].is_author = acc['is_author']

        self._contributors = None


    # access control

    def get_contributors(self):
        if self._contributors is None:
            self._contributors = sorted(self.model.contributors, key=lambda x: x.id)
        return self._contributors

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
        elif f and not f - {'date', 'draft', 'approved'}:
            with current_app.sphinx as sphinx:
                sphinx.update('stories', fields={'published': int(story.published)}, id=story.id)
                sphinx.update('chapters', fields={'published': int(story.published)}, id__in=[x.id for x in story.chapters])
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


class ChapterBL(BaseBL):
    def create(self, story, editor, data):
        from mini_fiction.models import Chapter

        new_order = orm.select(orm.max(x.order) for x in Chapter if x.story == story).first()

        chapter = self.model(
            story=story,
            title=data['title'],
            notes=data['notes'],
            text=data['text'],
            draft=True,
            story_published=story.published,
        )
        chapter.order = (new_order or 0) + 1

        self._update_words_count(chapter)
        chapter.flush()
        chapter.bl.edit_log(editor, 'add', {})
        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        return chapter

    def edit_log(self, editor, action, data, chapter_text_diff=None):
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

        if 'text' in data and data['text'] != chapter.text:
            from mini_fiction.utils import diff as utils_diff

            if len(chapter.text) <= current_app.config['MAX_SIZE_FOR_DIFF'] and len(data['text']) <= current_app.config['MAX_SIZE_FOR_DIFF']:
                # Для небольших текстов используем дифф на питоне, который красивый, но не быстрый
                chapter_text_diff = utils_diff.get_diff_default(chapter.text, data['text'])
            else:
                try:
                    # Для больших текстов используем библиотеку на C++, которая даёт диффы быстро, но не очень красиво
                    import diff_match_patch  # pylint: disable=W0612
                except ImportError:
                    # Если библиотеки нет, то и дифф не получился
                    chapter_text_diff = [('-', chapter.text), ('+', data['text'])]
                else:
                    chapter_text_diff = utils_diff.get_diff_google(chapter.text, data['text'])

            chapter.text = data['text']
            self._update_words_count(chapter)

        chapter.bl.edit_log(editor, 'edit', edited_data, chapter_text_diff=chapter_text_diff)

        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        return chapter

    def _update_words_count(self, chapter):
        old_words = chapter.words
        new_words = len(Markup.striptags(chapter.text).split())
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

        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)

    def viewed(self, user):
        if not user.is_authenticated:
            return

        from mini_fiction.models import StoryView

        chapter = self.model
        story = chapter.story
        view = StoryView.get(story=story, chapter=chapter, author=user)
        if not view:
            view = StoryView(
                story=story,
                chapter=chapter,
                author=user,
            )
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
