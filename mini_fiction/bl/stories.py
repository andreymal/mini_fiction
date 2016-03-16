#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import random
import ipaddress
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

    def create(self, authors, data):
        from mini_fiction.models import Category, Character, Classifier, Author, CoAuthorsStory

        data = Validator(STORY).validated(data)

        story = self.model(
            title=data['title'],
            summary=data['summary'],
            rating=data['rating'],
            original=data['original'],
            freezed=data['freezed'],
            finished=data['finished'],
            notes=data['notes'],
        )
        story.flush()
        story.categories.add(Category.select(lambda x: x.id in data['categories'])[:])
        story.characters.add(Character.select(lambda x: x.id in data['characters'])[:])
        story.classifications.add(Classifier.select(lambda x: x.id in data['classifications'])[:])
        for author, approved in authors:
            author = author
            CoAuthorsStory(
                story=story,
                author=author,
                approved=approved,
            ).flush()

        later(current_app.tasks['sphinx_update_story'].delay, story.id, ())
        return story

    def update(self, editor, data):
        from mini_fiction.models import StoryEditLogItem, Category, Character, Classifier, Rating

        data = Validator(STORY).validated(data, update=True)

        story = self.model
        old_published = story.published  # for chapters in search

        for key in ('title', 'summary', 'notes', 'original', 'finished', 'freezed'):
            if key in data:
                setattr(story, key, data[key])

        if 'rating' in data:
            story.rating = Rating.get(id=data['rating'])

        # TODO: refactor
        if 'categories' in data:
            story.categories.clear()
            story.categories.add(Category.select(lambda x: x.id in data['categories'])[:])
        if 'characters' in data:
            story.characters.clear()
            story.characters.add(Character.select(lambda x: x.id in data['characters'])[:])
        if 'classifications' in data:
            story.classifications.clear()
            story.classifications.add(Classifier.select(lambda x: x.id in data['classifications'])[:])

        if editor:
            sl_action = StoryEditLogItem.Actions.Edit
            if tuple(data.keys()) == ('approved',):
                sl_action = StoryEditLogItem.Actions.Approve if data['approved'] else StoryEditLogItem.Actions.Unapprove
            elif tuple(data.keys()) == ('draft',):
                sl_action = StoryEditLogItem.Actions.Publish if not data['draft'] else StoryEditLogItem.Actions.Unpublish
            sl = StoryEditLogItem(
                action=sl_action,
                user=editor,
                story=story,
            )
            sl.is_staff = editor.is_staff
            if sl_action == StoryEditLogItem.Actions.Edit:
                sl.data = data
            sl.flush()
        later(current_app.tasks['sphinx_update_story'].delay, story.id, ())
        return story

    def approve(self, user, approved):
        story = self.model
        old_published = story.published

        story.approved = bool(approved)
        if old_published != story.published:
            later(current_app.tasks['sphinx_update_story'].delay, story.id, ('approved',))
            for c in story.chapters:
                later(current_app.tasks['sphinx_update_chapter'].delay, c.id)
            for c in story.comments:  # TODO: update StoryComment where story = story.id
                c.story_published = story.published

    def publish(self, user, published):
        story = self.model
        old_published = story.published

        if story.publishable or (not story.draft and not story.publishable):
            story.draft = not published
            if old_published != story.published:
                later(current_app.tasks['sphinx_update_story'].delay, story.id, ('draft',))
                for c in story.chapters:
                    later(current_app.tasks['sphinx_update_chapter'].delay, c.id)
                for c in story.comments:
                    c.story_published = story.published
            return True

        return False

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
        if story.is_author(user):
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

    # access control

    def is_author(self, author):
        return (
            author and author.is_authenticated and
            author.id in [x.author.id for x in self.model.coauthors]
        )

    def editable_by(self, author):
        return author and (author.is_staff or self.is_author(author))

    def deletable_by(self, author):
        return self.is_author(author)

    def has_access(self, user=None):
        story = self.model
        if user and user.is_staff:
            return True
        if story.published or self.is_author(user) or self.editable_by(user):
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

    def can_comment_by(self, author=None):
        from mini_fiction.models import StoryComment
        return StoryComment.bl.can_comment_by(self.model, author)

    def create_comment(self, author, ip, data):
        from mini_fiction.models import StoryComment
        return StoryComment.bl.create(self.model, author, ip, data)

    def select_comments(self):
        from mini_fiction.models import StoryComment
        return orm.select(c for c in StoryComment if c.story == self.model)

    def last_viewed_comment_by(self, author):
        if author and author.is_authenticated:
            act = self.model.activity.select(lambda x: x.author.id == author.id).first()
            return act.last_comment_id if act else None
        else:
            return None


class ChapterBL(BaseBL):
    def create(self, story, title, notes='', text=''):
        from mini_fiction.models import Chapter

        new_order = orm.select(orm.max(x.order) for x in Chapter if x.story == story).first()

        chapter = self.model(
            story=story,
            title=title,
            notes=notes,
            text=text,
        )
        chapter.order = (new_order or 0) + 1
        self._update_words_count(chapter)
        chapter.flush()
        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        return chapter

    def update(self, **data):

        chapter = self.model
        if 'title' in data:
            chapter.title = data['title']
        if 'notes' in data:
            chapter.notes = data['notes']
        if 'text' in data:
            chapter.text = data['text']
            self._update_words_count(chapter)
        later(current_app.tasks['sphinx_update_chapter'].delay, chapter.id)
        return chapter

    def _update_words_count(self, chapter):
        old_words = chapter.words
        new_words = len(Markup.striptags(chapter.text).split())
        if new_words != chapter.words:
            chapter.words = new_words
            story = chapter.story
            story.words = story.words - old_words + new_words

    def delete(self):
        from mini_fiction.models import Chapter

        chapter = self.model
        story = chapter.story
        story.words = story.words - chapter.words
        later(current_app.tasks['sphinx_delete_chapter'].delay, story.id, chapter.id)

        old_order = chapter.order
        chapter.delete()

        for c in Chapter.select(lambda x: x.story == story and x.order > old_order):
            c.order = c.order - 1

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
            'published': chapter.story.published
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
