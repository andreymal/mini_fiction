#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import ipaddress
from datetime import datetime

from pony import orm
from flask import Markup, url_for, current_app
from flask_login import AnonymousUserMixin, UserMixin

from mini_fiction.database import db
from mini_fiction.bl.registry import Resource
from mini_fiction.filters import filter_html, filtered_html_property
from mini_fiction.filters.base import html_doc_to_string
from mini_fiction.filters.html import footnotes_to_html


class AnonymousUser(AnonymousUserMixin):
    id = None
    username = ''
    is_active = False
    is_staff = False
    is_superuser = False
    nsfw = False


class Author(db.Entity, UserMixin):
    """Модель автора"""

    # ported from django user
    password = orm.Optional(str, 255)
    last_login = orm.Optional(datetime, 6)
    is_superuser = orm.Required(bool, default=False)
    username = orm.Required(str, 32, unique=True, autostrip=False)
    first_name = orm.Optional(str, 30)
    last_name = orm.Optional(str, 30)
    email = orm.Optional(str, 254, index=True)
    is_staff = orm.Required(bool, default=False)
    is_active = orm.Required(bool, default=True)
    date_joined = orm.Required(datetime, 6, default=datetime.utcnow)

    bio = orm.Optional(orm.LongStr)
    excluded_categories = orm.Optional(str, 200)  # TODO: use it on index page
    detail_view = orm.Required(bool, default=False)
    nsfw = orm.Required(bool, default=False)
    comments_maxdepth = orm.Optional(int, size=16, unsigned=True, nullable=True, default=None)
    comment_spoiler_threshold = orm.Optional(int, size=16, nullable=True, default=None)

    avatar_small = orm.Optional(str, 255)
    avatar_medium = orm.Optional(str, 255)
    avatar_large = orm.Optional(str, 255)

    registration_profile = orm.Optional('RegistrationProfile')
    password_reset_profiles = orm.Set('PasswordResetProfile')
    contacts = orm.Set('Contact')
    coauthorstories = orm.Set('CoAuthorsStory')
    coauthorseries = orm.Set('CoAuthorsSeries')
    beta_reading = orm.Set('BetaReading')
    favorites = orm.Set('Favorites')
    bookmarks = orm.Set('Bookmark')
    edit_log = orm.Set('StoryLog')
    views = orm.Set('StoryView')
    activity = orm.Set('Activity')
    votes = orm.Set('Vote')
    story_comments = orm.Set('StoryComment')
    story_comment_votes = orm.Set('StoryCommentVote')
    story_comment_edits = orm.Set('StoryCommentEdit')
    notices = orm.Set('Notice')
    notice_comments = orm.Set('NoticeComment')
    notice_comment_votes = orm.Set('NoticeCommentVote')
    notice_comment_edits = orm.Set('NoticeCommentEdit')

    bl = Resource('bl.author')

    bio_as_html = filtered_html_property('bio', filter_html)

    @property
    def stories(self):
        return orm.select(x.story for x in CoAuthorsStory if x.author == self).without_distinct()

    @property
    def beta_stories(self):
        return orm.select(x.story for x in BetaReading if x.beta == self).without_distinct()

    @property
    def series(self):
        return orm.select(x.series for x in CoAuthorsSeries if x.author == self).without_distinct()

    @property
    def excluded_categories_list(self):
        return [int(x) for x in self.excluded_categories.split(',') if x]


class RegistrationProfile(db.Entity):
    activation_key = orm.Required(str, 40, unique=True)
    user = orm.Required(Author, unique=True)
    activated = orm.Required(bool, default=False)


class PasswordResetProfile(db.Entity):
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    activation_key = orm.Required(str, 40, unique=True)
    user = orm.Required(Author)
    activated = orm.Required(bool, default=False)


class Contact(db.Entity):
    """ Модель контакта пользователя """
    author = orm.Required(Author)
    name = orm.Required(str, 64)
    value = orm.Required(str, 255)


class CharacterGroup(db.Entity):
    """ Модель группы персонажа """

    name = orm.Required(str, 256)
    description = orm.Optional(orm.LongStr)

    characters = orm.Set('Character')

    bl = Resource('bl.charactergroup')


class Character(db.Entity):
    """ Модель персонажа """

    description = orm.Optional(orm.LongStr)
    name = orm.Required(str, 256)
    group = orm.Optional(CharacterGroup)
    picture = orm.Required(str, 128)

    stories = orm.Set('Story')

    bl = Resource('bl.character')

    @property
    def thumb(self):
        return url_for('media', filename=self.picture)


class Category(db.Entity):
    """ Модель жанра """

    description = orm.Optional(orm.LongStr)
    name = orm.Required(str, 256)
    color = orm.Required(str, 7, default='#808080')

    stories = orm.Set('Story')

    bl = Resource('bl.category')


class Classifier(db.Entity):
    """ Модель события """

    description = orm.Optional(orm.LongStr)
    name = orm.Required(str, 256)

    stories = orm.Set('Story')

    bl = Resource('bl.classifier')


class Rating(db.Entity):
    """ Модель рейтинга """

    description = orm.Optional(orm.LongStr)
    name = orm.Required(str, 256)

    stories = orm.Set('Story')


class InSeriesPermissions(db.Entity):
    """ Промежуточная модель хранения взаимосвязей рассказов, серий и разрешений на добавления рассказов в серии """

    story = orm.Optional('Story')
    series = orm.Optional('Series')
    order = orm.Required(int, size=16, unsigned=True, default=1)
    request = orm.Required(bool, default=False)
    answer = orm.Required(bool, default=False)


class Series(db.Entity):
    """ Модель серии """

    coauthors = orm.Set('CoAuthorsSeries')
    cover = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    draft = orm.Required(bool, default=True)
    finished = orm.Required(bool, default=False)
    freezed = orm.Required(bool, default=False)
    mark = orm.Required(int, size=16, default=0)
    notes = orm.Optional(orm.LongStr)
    original = orm.Required(bool, default=True)
    summary = orm.Optional(orm.LongStr, lazy=False)
    title = orm.Required(str, 512)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    views = orm.Required(int, default=0)

    permissions = orm.Set(InSeriesPermissions)

    def before_update(self):
        self.updated = datetime.utcnow()

    @property
    def stories(self):
        return orm.select(x.story for x in InSeriesPermissions if x.series == self).without_distinct().order_by('x.id')


class Story(db.Entity):
    """ Модель рассказа """

    title = orm.Required(str, 512)
    coauthors = orm.Set('CoAuthorsStory')
    characters = orm.Set(Character)
    categories = orm.Set(Category)
    classifications = orm.Set(Classifier)
    cover = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    first_published_at = orm.Optional(datetime, 6, index=True)
    draft = orm.Required(bool, default=True)
    approved = orm.Required(bool, default=False)
    finished = orm.Required(bool, default=False)
    freezed = orm.Required(bool, default=False)
    favorites = orm.Set('Favorites')
    bookmarks = orm.Set('Bookmark')
    notes = orm.Optional(orm.LongStr)
    original = orm.Required(bool, default=True)
    rating = orm.Required(Rating)
    summary = orm.Required(orm.LongStr, lazy=False)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    words = orm.Required(int, default=0)
    vote_total = orm.Required(int, unsigned=True, default=0)
    vote_average = orm.Required(float, default=3)
    vote_average_index = orm.Required(int, size=16, unsigned=True, default=300)  # float can't be used with composite_index
    vote_stddev = orm.Required(float, default=0)
    comments_count = orm.Required(int, size=16, unsigned=True, default=0)
    source_link = orm.Optional(str, 255)
    source_title = orm.Optional(str, 255)

    in_series_permissions = orm.Set(InSeriesPermissions)
    chapters = orm.Set('Chapter')
    edit_log = orm.Set('StoryLog')
    story_views_set = orm.Set('StoryView')
    activity = orm.Set('Activity')
    votes = orm.Set('Vote')
    comments = orm.Set('StoryComment')
    beta_reading = orm.Set('BetaReading')

    orm.composite_index(approved, draft)
    orm.composite_index(approved, draft, first_published_at)
    orm.composite_index(approved, draft, vote_average_index)

    bl = Resource('bl.story')

    def before_update(self):
        self.updated = datetime.utcnow()
        vote_average_index = round(self.vote_average * 100)
        if vote_average_index != self.vote_average_index:
            self.vote_average_index = vote_average_index

    @property
    def url(self):
        return url_for('story.view', pk=self.id)

    @property
    def authors(self):
        return orm.select(x.author for x in CoAuthorsStory if x.story == self).without_distinct().order_by('x.id')

    @property
    def betas(self):
        return orm.select(x.beta for x in BetaReading if x.story == self).without_distinct().order_by('x.id')

    @property
    def in_series(self):
        return orm.select(x.series for x in InSeriesPermissions if x.story == self).without_distinct().order_by('x.id')

    @property
    def published(self):
        return bool(self.approved and not self.draft)

    # Количество просмотров
    @property
    def views(self):
        # orm.count() uses DISTINCT
        # TODO: refactor to field
        return orm.select(orm.count(x.author) for x in StoryView if x.story == self).first()

    @classmethod
    def select_published(cls):
        return cls.select(lambda x: x.approved and not x.draft)

    @classmethod
    def select_submitted(cls):
        return cls.select(lambda x: not x.approved and not x.draft)

    def favorited(self, user_id):
        return self.favorites.select(lambda x: x.author.id == user_id).exists()

    def bookmarked(self, user_id):
        return self.bookmarks.select(lambda x: x.author.id == user_id).exists()

    # Дельта количества последних добавленных комментариев с момента посещения юзером рассказа
    def last_comments_by_author(self, author):
        act = self.activity.select(lambda x: x.author.id == author.id).first()
        return act.last_comments if act else 0

    @classmethod
    def accessible(cls, user):
        default_queryset = cls.select(lambda x: x.approved and not x.draft)
        if not user.is_authenticated:
            return default_queryset
        if user.is_staff:
            return cls.select()
        else:
            return default_queryset

    # Проверка авторства
    def editable_by(self, author):
        # TODO: remove
        return self.bl.editable_by(author)

    def deletable_by(self, user):
        # TODO: remove
        return self.bl.deletable_by(user)

    def is_author(self, author):
        # TODO: remove
        return self.bl.is_author(author)

    # Проверка возможности публикации
    @property
    def publishable(self):
        return True if self.words >= current_app.config['PUBLISH_SIZE_LIMIT'] else False

    @property
    def nsfw(self):
        return True if self.rating.id in current_app.config['NSFW_RATING_IDS'] else False

    summary_as_html = filtered_html_property('summary', filter_html)
    notes_as_html = filtered_html_property('notes', filter_html)

    def list_downloads(self):
        from mini_fiction.downloads import list_formats
        downloads = []
        for f in list_formats():
            downloads.append({
                'format': f,
                'url': f.url(self),
            })
        return downloads


class Chapter(db.Entity):
    """ Модель главы """

    date = orm.Required(datetime, 6, default=datetime.utcnow)
    story = orm.Required(Story)
    mark = orm.Required(int, size=16, unsigned=True, default=0)
    notes = orm.Optional(orm.LongStr)
    order = orm.Required(int, size=16, unsigned=True, default=1)
    title = orm.Required(str, 512)
    text = orm.Optional(orm.LongStr)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    words = orm.Required(int, default=0)
    story_published = orm.Required(bool)  # optimization of stream pages
    edit_log = orm.Set('StoryLog')

    orm.composite_index(date, story_published)

    bl = Resource('bl.chapter')

    chapter_views_set = orm.Set('StoryView')

    def before_update(self):
        self.updated = datetime.utcnow()
        self.story.updated = datetime.utcnow()  # for downloading

    def get_absolute_url(self):
        return url_for('chapter.view_single', story_id=self.story.id, order=self.order)

    def get_prev_chapter(self):
        order = self.order - 1
        return orm.select(x for x in Chapter if x.story == self.story and x.order == order).first()

    def get_next_chapter(self):
        order = self.order + 1
        return orm.select(x for x in Chapter if x.story == self.story and x.order == order).first()

    @property
    def published(self):
        return self.story.published

    # Количество просмотров
    @property
    def views(self):
        return orm.select(orm.count(x.author) for x in StoryView if x.story == self.story and x.chapter == self).first()

    def editable_by(self, author):
        return self.story.editable_by(author)

    notes_as_html = filtered_html_property('notes', filter_html)

    @property
    def text_as_html(self):
        try:
            doc = self.get_filtered_chapter_text()
            doc = footnotes_to_html(doc)
            return Markup(html_doc_to_string(doc))
        except:
            if current_app.config['DEBUG']:
                import traceback
                return traceback.format_exc()
            return "#ERROR#"

    def get_filtered_chapter_text(self):
        return filter_html(
            self.text,
            tags=current_app.config['CHAPTER_ALLOWED_TAGS'],
            attributes=current_app.config['CHAPTER_ALLOWED_ATTRIBUTES'],
        )


class CoAuthorsStory(db.Entity):
    """ Промежуточная модель хранения взаимосвязей авторства рассказов (включая соавторов) """

    author = orm.Required(Author)
    story = orm.Required(Story)
    approved = orm.Required(bool, default=False)


class CoAuthorsSeries(db.Entity):
    """ Промежуточная модель хранения взаимосвязей авторства серий (включая соавторов) """

    author = orm.Optional(Author)
    series = orm.Optional(Series)
    approved = orm.Required(bool, default=False)


class BetaReading(db.Entity):
    """ Промежуточная модель хранения взаимосвязей рассказов, бета-читателей и результатов вычитки """

    beta = orm.Optional(Author)
    story = orm.Optional(Story)
    checked = orm.Required(bool, default=False)


class StoryComment(db.Entity):
    """ Модель комментария к рассказу """

    id = orm.PrimaryKey(int, auto=True)
    local_id = orm.Required(int)
    parent = orm.Optional('StoryComment', reverse='answers', nullable=True, default=None)
    author = orm.Optional(Author, nullable=True, default=None)
    author_username = orm.Optional(str, 64)  # На случай, если учётную запись автора удалят
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    deleted = orm.Required(bool, default=False)
    last_deleted_at = orm.Optional(datetime, 6)
    story = orm.Required(Story)
    text = orm.Required(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)
    vote_count = orm.Required(int, size=16, unsigned=True, default=0)
    vote_total = orm.Required(int, default=0)

    # Optimizations
    tree_depth = orm.Required(int, size=16, unsigned=True, default=0)
    answers_count = orm.Required(int, size=16, unsigned=True, default=0)
    edits_count = orm.Required(int, size=16, unsigned=True, default=0)
    root_order = orm.Required(int, size=16, unsigned=True)  # for pagination
    story_published = orm.Required(bool)
    last_edited_at = orm.Optional(datetime, 6)  # only for text updates

    votes = orm.Set('StoryCommentVote')
    edits = orm.Set('StoryCommentEdit')
    answers = orm.Set('StoryComment', reverse='parent')

    bl = Resource('bl.story_comment')

    orm.composite_key(story, local_id)
    orm.composite_index(deleted, story_published)
    orm.composite_index(author, deleted, story_published)
    orm.composite_index(story, root_order, tree_depth)

    @property
    def brief_text(self):
        text = self.text
        if len(text) > current_app.config['BRIEF_COMMENT_LENGTH']:
            text = text[:current_app.config['BRIEF_COMMENT_LENGTH']] + '...'
        return text

    text_as_html = filtered_html_property('text', filter_html)
    brief_text_as_html = filtered_html_property('brief_text', filter_html)

    def before_update(self):
        self.updated = datetime.utcnow()


class StoryCommentEdit(db.Entity):
    """ Модель с информацией о редактировании комментария к рассказу """

    comment = orm.Required(StoryComment)
    editor = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    old_text = orm.Optional(orm.LongStr, lazy=False)
    new_text = orm.Optional(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)


class StoryCommentVote(db.Entity):
    """ Модель голосования за комментарий к рассказу """

    comment = orm.Required(StoryComment)
    author = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    vote_value = orm.Required(int, default=0)


class Vote(db.Entity):
    """ Модель голосований """

    author = orm.Optional(Author)
    story = orm.Optional(Story)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)
    vote_value = orm.Required(int, size=16, unsigned=True, default=3)

    def before_update(self):
        self.updated = datetime.utcnow()


class Favorites(db.Entity):
    """ Модель избранного """
    author = orm.Required(Author)
    story = orm.Required(Story)
    date = orm.Required(datetime, 6, default=datetime.utcnow)


class Bookmark(db.Entity):
    """ Модель закладок """
    author = orm.Required(Author)
    story = orm.Required(Story)
    date = orm.Required(datetime, 6, default=datetime.utcnow)


class StoryView(db.Entity):
    """ Модель просмотров """
    # NOTE: Будет расширена и переименована для серий
    author = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    story = orm.Optional(Story)
    chapter = orm.Optional(Chapter)


class Activity(db.Entity):
    """ Модель отслеживания активности """

    author = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    story = orm.Optional(Story)
    last_views = orm.Required(int, default=0)
    last_comments = orm.Required(int, default=0)
    last_vote_average = orm.Required(float, default=3)
    last_vote_stddev = orm.Required(float, default=0)
    last_comment_id = orm.Required(int, default=0)


class StoryLog(db.Entity):
    created_at = orm.Required(datetime, 6, default=datetime.utcnow, index=True)
    user = orm.Required(Author)
    story = orm.Required(Story)

    chapter_action = orm.Optional(str, 12, py_check=lambda x: x in {'', 'add', 'edit', 'delete'})
    chapter = orm.Optional(Chapter)
    chapter_title = orm.Optional(orm.LongStr, lazy=False)  # На случай, если главу удалят
    # если chapter_action пуст, data_json относится к рассказу, иначе к главе (кроме text)
    data_json = orm.Required(orm.LongStr, lazy=False)  # {key: [old_value, new_value]}
    by_staff = orm.Required(bool, default=False)

    # [["=", длина], ["-", "удалённый кусок"], ["+", "добавленный кусок"]]
    # Дифф перевёрнутый: для получения старого текста нужно применить его к новому!
    chapter_text_diff = orm.Optional(orm.LongStr)

    orm.composite_index(story, created_at)
    orm.composite_index(by_staff, created_at)

    @property
    def data(self):
        return json.loads(self.data_json)


class Notice(db.Entity):
    """ Модель объявления """

    name = orm.Required(str, 64, index=True, unique=True)
    show = orm.Required(bool, default=False, index=True)
    author = orm.Required(Author)
    title = orm.Required(str, 192)
    content = orm.Optional(orm.LongStr)
    is_template = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)

    comments_count = orm.Required(int, size=16, unsigned=True, default=0)
    comments = orm.Set('NoticeComment')

    bl = Resource('bl.notice')

    def before_update(self):
        self.updated = datetime.utcnow()


class NoticeComment(db.Entity):
    """ Модель комментария к объявлению """

    id = orm.PrimaryKey(int, auto=True)
    local_id = orm.Required(int)
    parent = orm.Optional('NoticeComment', reverse='answers', nullable=True, default=None)
    author = orm.Optional(Author, nullable=True, default=None)
    author_username = orm.Optional(str, 64)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    deleted = orm.Required(bool, default=False)
    last_deleted_at = orm.Optional(datetime, 6)
    notice = orm.Required(Notice)
    text = orm.Required(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)
    vote_count = orm.Required(int, size=16, unsigned=True, default=0)
    vote_total = orm.Required(int, default=0)

    # Optimizations
    tree_depth = orm.Required(int, size=16, unsigned=True, default=0)
    answers_count = orm.Required(int, size=16, unsigned=True, default=0)
    edits_count = orm.Required(int, size=16, unsigned=True, default=0)
    root_order = orm.Required(int, size=16, unsigned=True)  # for pagination
    last_edited_at = orm.Optional(datetime, 6)  # only for text updates

    votes = orm.Set('NoticeCommentVote')
    edits = orm.Set('NoticeCommentEdit')
    answers = orm.Set('NoticeComment', reverse='parent')

    bl = Resource('bl.notice_comment')

    orm.composite_key(notice, local_id)
    orm.composite_index(notice, root_order, tree_depth)

    @property
    def brief_text(self):
        text = self.text
        if len(text) > current_app.config['BRIEF_COMMENT_LENGTH']:
            text = text[:current_app.config['BRIEF_COMMENT_LENGTH']] + '...'
        return text

    text_as_html = filtered_html_property('text', filter_html)
    brief_text_as_html = filtered_html_property('brief_text', filter_html)

    def before_update(self):
        self.updated = datetime.utcnow()


class NoticeCommentEdit(db.Entity):
    """ Модель с информацией о редактировании комментария к объявлению """

    comment = orm.Required(NoticeComment)
    editor = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    old_text = orm.Optional(orm.LongStr, lazy=False)
    new_text = orm.Optional(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)


class NoticeCommentVote(db.Entity):
    """ Модель голосования за комментарий к объявлению """

    comment = orm.Required(NoticeComment)
    author = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    vote_value = orm.Required(int, default=0)


class StaticPage(db.Entity):
    name = orm.Required(str, 64)
    lang = orm.Optional(str, 4)
    orm.composite_key(name, lang)
    title = orm.Optional(str, 192)
    content = orm.Optional(orm.LongStr)
    is_template = orm.Required(bool, default=False)
    is_full_page = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)

    bl = Resource('bl.staticpage')

    def before_update(self):
        self.updated = datetime.utcnow()


class HtmlBlock(db.Entity):
    name = orm.Required(str, 64)
    lang = orm.Optional(str, 4)
    content = orm.Optional(orm.LongStr)
    is_template = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)

    orm.composite_key(name, lang)

    bl = Resource('bl.htmlblock')

    def before_update(self):
        self.updated = datetime.utcnow()
