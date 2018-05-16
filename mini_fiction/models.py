#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import ipaddress
from datetime import datetime

from pony import orm
from flask_babel import gettext
from flask import Markup, url_for, current_app
from flask_login import AnonymousUserMixin, UserMixin

from mini_fiction.database import db
from mini_fiction.bl.registry import Resource
from mini_fiction.filters import filter_html, filtered_html_property
from mini_fiction.utils.misc import htmlcrop


class Logopic(db.Entity):
    """ Модель картинки в шапке сайта """

    picture = orm.Required(str, 255)
    sha256sum = orm.Required(str, 64)
    visible = orm.Required(bool, default=True)
    description = orm.Optional(orm.LongStr)
    original_link = orm.Optional(str, 255)
    original_link_label = orm.Optional(orm.LongStr, lazy=False)
    created_at = orm.Required(datetime, 6, default=datetime.utcnow)
    updated_at = orm.Required(datetime, 6, default=datetime.utcnow)

    bl = Resource('bl.logopic')

    @property
    def url(self):
        return url_for('media', filename=self.picture, v=self.sha256sum[:6])


class AnonymousUser(AnonymousUserMixin):
    id = None
    username = ''
    is_active = False
    is_staff = False
    is_superuser = False
    nsfw = False
    comments_per_page = None
    comments_maxdepth = None
    comment_spoiler_threshold = None
    header_mode = ''


class Author(db.Entity, UserMixin):
    """Модель автора"""

    password = orm.Optional(str, 255)
    last_password_change = orm.Optional(datetime, 6, optimistic=False, default=datetime.utcnow)
    last_login = orm.Optional(datetime, 6, optimistic=False)
    last_visit = orm.Optional(datetime, 6, optimistic=False)
    is_superuser = orm.Required(bool, default=False, optimistic=False)
    username = orm.Required(str, 32, unique=True, autostrip=False)
    first_name = orm.Optional(str, 30, autostrip=False)
    last_name = orm.Optional(str, 30, autostrip=False)
    email = orm.Optional(str, 254, index=True)
    is_staff = orm.Required(bool, default=False, optimistic=False)
    is_active = orm.Required(bool, default=True, optimistic=False)
    date_joined = orm.Required(datetime, 6, default=datetime.utcnow, optimistic=False)  # Дата отправки формы регистрации
    activated_at = orm.Optional(datetime, 6, optimistic=False)  # Дата перехода по ссылке активации из письма
    session_token = orm.Required(str, 32, optimistic=False)

    premoderation_mode = orm.Optional(str, 8, py_check=lambda x: x in {'', 'off', 'on'})

    bio = orm.Optional(orm.LongStr, autostrip=False)
    excluded_categories = orm.Optional(str, 200)  # TODO: use it on index page
    detail_view = orm.Required(bool, default=False)
    nsfw = orm.Required(bool, default=False)
    comments_per_page = orm.Optional(int, size=16, unsigned=True, nullable=True, default=None)
    comments_maxdepth = orm.Optional(int, size=16, unsigned=True, nullable=True, default=None)
    comment_spoiler_threshold = orm.Optional(int, size=16, nullable=True, default=None)
    header_mode = orm.Optional(str, 8, py_check=lambda x: x in {'', 'off', 'l', 'ls'})

    # Если хранить подписки наизнанку, проще регистрировать народ и добавлять
    # новые типы подписок
    silent_email = orm.Optional(orm.LongStr, lazy=False)
    silent_tracker = orm.Optional(orm.LongStr, lazy=False)
    last_viewed_notification_id = orm.Required(int, default=0, optimistic=False)

    avatar_small = orm.Optional(str, 255)
    avatar_medium = orm.Optional(str, 255)
    avatar_large = orm.Optional(str, 255)

    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    password_reset_profiles = orm.Set('PasswordResetProfile')
    change_email_profiles = orm.Set('ChangeEmailProfile')
    contacts = orm.Set('Contact')
    contributing = orm.Set('StoryContributor')
    coauthorseries = orm.Set('CoAuthorsSeries')
    approvals = orm.Set('Story', reverse='approved_by')
    published_stories = orm.Set('Story', reverse='published_by_author')
    favorites = orm.Set('Favorites')
    bookmarks = orm.Set('Bookmark')
    edit_log = orm.Set('StoryLog')
    views = orm.Set('StoryView')
    activity = orm.Set('Activity')
    votes = orm.Set('Vote')
    story_comments = orm.Set('StoryComment', reverse='author')
    story_comment_votes = orm.Set('StoryCommentVote')
    story_comment_edits = orm.Set('StoryCommentEdit')
    story_last_edited_comments = orm.Set('StoryComment', reverse='last_edited_by')
    story_deleted_comments = orm.Set('StoryComment', reverse='last_deleted_by')
    story_local_comments = orm.Set('StoryLocalComment', reverse='author')
    story_local_comment_edits = orm.Set('StoryLocalCommentEdit')
    story_local_last_edited_comments = orm.Set('StoryLocalComment', reverse='last_edited_by')
    story_local_deleted_comments = orm.Set('StoryLocalComment', reverse='last_deleted_by')
    news = orm.Set('NewsItem')
    news_comments = orm.Set('NewsComment', reverse='author')
    news_comment_votes = orm.Set('NewsCommentVote')
    news_comment_edits = orm.Set('NewsCommentEdit')
    news_last_edited_comments = orm.Set('NewsComment', reverse='last_edited_by')
    news_deleted_comments = orm.Set('NewsComment', reverse='last_deleted_by')
    notifications = orm.Set('Notification', reverse='user')
    created_notifications = orm.Set('Notification', reverse='caused_by_user')
    subscriptions = orm.Set('Subscription')
    abuse_reports = orm.Set('AbuseReport')
    admin_log = orm.Set('AdminLog')

    bl = Resource('bl.author')

    bio_as_html = filtered_html_property('bio', filter_html)

    def __str__(self):
        return self.username

    def get_id(self):
        # for flask-login
        return '{}#{}'.format(self.id, self.session_token)

    @property
    def contributing_stories(self):
        return orm.select(x.story for x in StoryContributor if x.user == self and not x.is_author).without_distinct()

    @property
    def stories(self):
        return orm.select(x.story for x in StoryContributor if x.user == self and x.is_author).without_distinct()

    @property
    def series(self):
        return orm.select(x.series for x in CoAuthorsSeries if x.author == self).without_distinct()

    @property
    def excluded_categories_list(self):
        return [int(x) for x in self.excluded_categories.split(',') if x]

    @property
    def silent_email_list(self):
        return self.silent_email.split(',')

    @property
    def silent_tracker_list(self):
        return self.silent_tracker.split(',')


class RegistrationProfile(db.Entity):
    activation_key = orm.Required(str, 40, unique=True)
    email = orm.Required(str, 254)
    password = orm.Optional(str, 255)
    username = orm.Required(str, 32, index=True, autostrip=False)
    created_at = orm.Required(datetime, 6, default=datetime.utcnow)

    def __str__(self):
        return 'Registration information for {}'.format(self.username)


class PasswordResetProfile(db.Entity):
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    activation_key = orm.Required(str, 40, unique=True)
    user = orm.Required(Author)
    activated = orm.Required(bool, default=False)

    def __str__(self):
        return 'Password reset information for {}'.format(self.user.username)


class ChangeEmailProfile(db.Entity):
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    activation_key = orm.Required(str, 40, unique=True)
    user = orm.Required(Author, unique=True)
    email = orm.Required(str, 254, index=True)

    def __str__(self):
        return '<Change email information for{}'.format(self.user.username)


class Contact(db.Entity):
    """ Модель контакта пользователя """
    author = orm.Required(Author)
    name = orm.Required(str, 64)
    value = orm.Required(str, 255)

    def __str__(self):
        return '<Contact {}/{}>'.format(self.author.username, self.name)


class CharacterGroup(db.Entity):
    """ Модель группы персонажа """

    name = orm.Required(str, 256)
    description = orm.Optional(orm.LongStr)

    characters = orm.Set('Character')

    bl = Resource('bl.charactergroup')

    def __str__(self):
        return self.name


class Character(db.Entity):
    """ Модель персонажа """

    description = orm.Optional(orm.LongStr)
    name = orm.Required(str, 256)
    group = orm.Optional(CharacterGroup)
    picture = orm.Required(str, 128)

    stories = orm.Set('Story')

    bl = Resource('bl.character')

    def __str__(self):
        return self.name

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

    def __str__(self):
        return self.name


class Classifier(db.Entity):
    """ Модель события """

    description = orm.Optional(orm.LongStr)
    name = orm.Required(str, 256)

    stories = orm.Set('Story')

    bl = Resource('bl.classifier')

    def __str__(self):
        return self.name


class Rating(db.Entity):
    """ Модель рейтинга """

    description = orm.Optional(orm.LongStr)
    name = orm.Required(str, 256)
    nsfw = orm.Required(bool, default=False)

    stories = orm.Set('Story')

    def __str__(self):
        return self.name


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
    summary = orm.Optional(orm.LongStr, lazy=False, autostrip=False)
    title = orm.Required(str, 512)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    views = orm.Required(int, default=0)
    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    permissions = orm.Set(InSeriesPermissions)

    def __str__(self):
        return self.title

    def before_update(self):
        self.updated = datetime.utcnow()

    @property
    def stories(self):
        return orm.select(x.story for x in InSeriesPermissions if x.series == self).without_distinct().order_by('x.id')


class Story(db.Entity):
    """ Модель рассказа """

    title = orm.Required(str, 512, autostrip=False)
    contributors = orm.Set('StoryContributor')
    characters = orm.Set(Character)
    categories = orm.Set(Category)
    classifications = orm.Set(Classifier)
    cover = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    first_published_at = orm.Optional(datetime, 6, index=True)
    draft = orm.Required(bool, default=True)
    approved = orm.Required(bool, default=False)
    # TODO: finished и freezed объединены в интерфейсе сайта,
    # стоит объединить и в базе тоже
    finished = orm.Required(bool, default=False)
    freezed = orm.Required(bool, default=False)
    favorites = orm.Set('Favorites')
    bookmarks = orm.Set('Bookmark')
    notes = orm.Optional(orm.LongStr, autostrip=False)
    original = orm.Required(bool, default=True)
    rating = orm.Required(Rating)
    summary = orm.Optional(orm.LongStr, lazy=False, autostrip=False)
    updated = orm.Required(datetime, 6, default=datetime.utcnow, optimistic=False)
    words = orm.Required(int, default=0, optimistic=False)
    views = orm.Required(int, default=0, optimistic=False)

    vote_total = orm.Required(int, unsigned=True, default=0, optimistic=False)  # TODO: rename to vote_count
    vote_value = orm.Required(int, default=0, optimistic=False)
    vote_extra = orm.Required(orm.LongStr, lazy=False, default='{}', optimistic=False)

    comments_count = orm.Required(int, size=16, unsigned=True, default=0, optimistic=False)
    source_link = orm.Optional(str, 255)
    source_title = orm.Optional(str, 255)
    pinned = orm.Required(bool, default=False)
    robots_noindex = orm.Required(bool, default=False)
    comments_mode = orm.Optional(str, 8, py_check=lambda x: x in {'', 'on', 'off', 'pub', 'nodraft'})
    direct_access = orm.Optional(str, 8, py_check=lambda x: x in {'', 'all', 'none', 'nodraft', 'anodraft'})
    approved_by = orm.Optional(Author)
    published_by_author = orm.Optional(Author)  # Ему будет отправлено уведомление о публикации
    last_author_notification_at = orm.Optional(datetime, 6)  # Во избежание слишком частых уведомлений
    last_staff_notification_at = orm.Optional(datetime, 6)
    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    in_series_permissions = orm.Set(InSeriesPermissions)
    chapters = orm.Set('Chapter')
    edit_log = orm.Set('StoryLog')
    story_views_set = orm.Set('StoryView')
    activity = orm.Set('Activity')
    votes = orm.Set('Vote')
    comments = orm.Set('StoryComment')
    local = orm.Optional('StoryLocalThread', cascade_delete=True)

    orm.composite_index(approved, draft)
    orm.composite_index(approved, draft, first_published_at)
    orm.composite_index(approved, draft, pinned, first_published_at)
    orm.composite_index(approved, draft, vote_value)

    bl = Resource('bl.story')

    def __str__(self):
        return self.title

    @property
    def url(self):
        return url_for('story.view', pk=self.id)

    @property
    def authors(self):
        return self.bl.get_authors()

    @property
    def published(self):
        return bool(self.approved and not self.draft)

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

    # Проверка возможности публикации
    @property
    def publishable(self):
        return self.words >= current_app.config['PUBLISH_SIZE_LIMIT']

    @property
    def nsfw(self):
        return self.rating.nsfw

    summary_as_html = filtered_html_property('summary', filter_html)
    notes_as_html = filtered_html_property('notes', filter_html)

    def list_downloads(self):
        from mini_fiction.downloads import list_formats
        downloads = []
        for f in list_formats():
            downloads.append({
                'format': f,
                'cls': f.name.lower().replace('+', '-').replace('/', '-'),
                'url': f.url(self),
            })
        return downloads

    @property
    def status_string(self):
        if self.finished:
            return 'finished'
        if self.freezed:
            return 'freezed'
        return 'unfinished'


class Chapter(db.Entity):
    """ Модель главы """

    date = orm.Required(datetime, 6, default=datetime.utcnow)
    story = orm.Required(Story)
    mark = orm.Required(int, size=16, unsigned=True, default=0)
    notes = orm.Optional(orm.LongStr, autostrip=False)
    order = orm.Required(int, size=16, unsigned=True, default=1)
    title = orm.Optional(str, 512, autostrip=False)
    text = orm.Optional(orm.LongStr, autostrip=False)
    text_md5 = orm.Required(str, 32, default='d41d8cd98f00b204e9800998ecf8427e')
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    words = orm.Required(int, default=0, optimistic=False)
    views = orm.Required(int, default=0, optimistic=False)
    # Глава опубликована только при draft=False и story_published=True
    draft = orm.Required(bool, default=True)
    story_published = orm.Required(bool)  # optimization of stream pages
    first_published_at = orm.Optional(datetime, 6)
    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    edit_log = orm.Set('StoryLog')

    orm.composite_key(story, order)
    orm.composite_index(first_published_at, order)

    bl = Resource('bl.chapter')

    chapter_views_set = orm.Set('StoryView')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return url_for('chapter.view_single', story_id=self.story.id, order=self.order)

    def get_prev_chapter(self, allow_draft=False):
        q = orm.select(x for x in Chapter if x.story == self.story and x.order < self.order).order_by(Chapter.order.desc())
        if not allow_draft:
            q = q.filter(lambda x: not x.draft)
        return q.first()

    def get_next_chapter(self, allow_draft=False):
        q = orm.select(x for x in Chapter if x.story == self.story and x.order > self.order).order_by(Chapter.order)
        if not allow_draft:
            q = q.filter(lambda x: not x.draft)
        return q.first()

    @property
    def notes_as_html(self):
        return self.bl.notes2html(self.notes)

    @property
    def text_as_html(self):
        return self.bl.text2html(self.text)

    @property
    def text_preview(self):
        text = self.text[:500]
        f = text.rfind(' ')
        if f >= 0 and len(text) == 500:
            text = text[:f]

        f = text.rfind('<')
        if f >= 0 and f > text.rfind('>'):
            text = text[:f]  # 'foo <stro' → 'foo '

        text = text.replace('</p>', '\n</p>').replace('<br', '\n<br')
        text = Markup(text).striptags().replace('\n', ' / ').replace('  ', ' ')
        if len(self.text) > 500:
            text += '...'
        return text

    @property
    def autotitle(self):
        # Если у главы нет заголовка, генерирует его
        if self.title:
            return self.title
        if self.order == 1:
            return self.story.title
        return gettext('Chapter {}').format(self.order)

    def get_filtered_chapter_text(self):
        return self.bl.filter_text(self.text)

    def get_fb2_chapter_text(self):
        # TODO: отрефакторить
        doc = self.bl.filter_text(self.text)
        if self.notes:
            body = doc.xpath('//body')[0]
            ann = self.bl.filter_text(self.notes).xpath('//body')[0]
            ann.tag = 'annotation'
            body.insert(0, ann)
        import lxml.etree
        return doc


class StoryContributor(db.Entity):
    """ Промежуточная модель хранения всех пользователей, участвовавших в написании рассказов """

    # is_editor, is_author:
    # - False, False — бета-читатель
    # - True, False — редактор
    # - True, True — автор (соавтор)
    # - False, True — автор, с которым поругались :)

    story = orm.Required(Story)
    user = orm.Required(Author)
    visible = orm.Required(bool, default=False)  # На авторов не влияет, у них всегда True
    is_editor = orm.Required(bool, default=False)
    is_author = orm.Required(bool, default=False)
    created_at = orm.Required(datetime, 6, default=datetime.utcnow)
    updated_at = orm.Required(datetime, 6, default=datetime.utcnow)

    def before_update(self):
        self.updated_at = datetime.utcnow()


class CoAuthorsSeries(db.Entity):
    """ Промежуточная модель хранения взаимосвязей авторства серий (включая соавторов) """

    author = orm.Optional(Author)
    series = orm.Optional(Series)
    approved = orm.Required(bool, default=False)


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
    last_deleted_at = orm.Optional(datetime, 6, index=True)
    last_deleted_by = orm.Optional(Author)
    story = orm.Required(Story)
    text = orm.Optional(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)
    vote_count = orm.Required(int, size=16, unsigned=True, default=0)
    vote_total = orm.Required(int, default=0)

    # Optimizations
    tree_depth = orm.Required(int, size=16, unsigned=True, default=0)
    answers_count = orm.Required(int, size=16, unsigned=True, default=0)
    edits_count = orm.Required(int, size=16, unsigned=True, default=0)
    root_id = orm.Required(int)  # for pagination
    story_published = orm.Required(bool)
    last_edited_at = orm.Optional(datetime, 6)  # only for text updates
    last_edited_by = orm.Optional(Author)  # only for text updates

    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    votes = orm.Set('StoryCommentVote')
    edits = orm.Set('StoryCommentEdit')
    answers = orm.Set('StoryComment', reverse='parent')

    bl = Resource('bl.story_comment')

    orm.composite_key(story, local_id)
    orm.composite_index(deleted, story_published)
    orm.composite_index(author, deleted, story_published)
    orm.composite_index(story, root_id, tree_depth)

    @property
    def brief_text(self):
        return htmlcrop(self.text, current_app.config['BRIEF_COMMENT_LENGTH'])

    @property
    def text_as_html(self):
        return self.bl.text2html(self.text)

    @property
    def brief_text_as_html(self):
        return self.bl.text2html(self.brief_text)

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


class StoryLocalThread(db.Entity):
    """ Временный костыль из-за ограниченной гибкости комментариев """
    story = orm.Required(Story, unique=True)
    comments_count = orm.Required(int, size=16, unsigned=True, default=0)
    comments = orm.Set('StoryLocalComment')

    bl = Resource('bl.story_local_thread')


class StoryLocalComment(db.Entity):
    """ Модель комментария к рассказу """

    id = orm.PrimaryKey(int, auto=True)
    local_id = orm.Required(int)
    parent = orm.Optional('StoryLocalComment', reverse='answers', nullable=True, default=None)
    author = orm.Optional(Author, nullable=True, default=None)
    author_username = orm.Optional(str, 64)  # На случай, если учётную запись автора удалят
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    deleted = orm.Required(bool, default=False)
    last_deleted_at = orm.Optional(datetime, 6, index=True)
    last_deleted_by = orm.Optional(Author)
    local = orm.Required(StoryLocalThread)
    text = orm.Optional(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)

    # Optimizations
    tree_depth = orm.Required(int, size=16, unsigned=True, default=0)
    answers_count = orm.Required(int, size=16, unsigned=True, default=0)
    edits_count = orm.Required(int, size=16, unsigned=True, default=0)
    root_id = orm.Required(int)  # for pagination
    last_edited_at = orm.Optional(datetime, 6)  # only for text updates
    last_edited_by = orm.Optional(Author)  # only for text updates

    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    edits = orm.Set('StoryLocalCommentEdit')
    answers = orm.Set('StoryLocalComment', reverse='parent')

    bl = Resource('bl.story_local_comment')

    orm.composite_key(local, local_id)

    @property
    def brief_text(self):
        return htmlcrop(self.text, current_app.config['BRIEF_COMMENT_LENGTH'])

    text_as_html = filtered_html_property('text', filter_html)
    brief_text_as_html = filtered_html_property('brief_text', filter_html)

    def before_update(self):
        self.updated = datetime.utcnow()


class StoryLocalCommentEdit(db.Entity):
    """ Модель с информацией о редактировании комментария к рассказу """

    comment = orm.Required(StoryLocalComment)
    editor = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    old_text = orm.Optional(orm.LongStr, lazy=False)
    new_text = orm.Optional(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)


class Vote(db.Entity):
    """ Модель голосований """

    author = orm.Optional(Author)
    story = orm.Optional(Story)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow, optimistic=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded, optimistic=False)
    vote_value = orm.Required(int, default=0, optimistic=False)
    revoked_at = orm.Optional(datetime, 6)
    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    orm.composite_key(author, story)


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
    last_views = orm.Required(int, default=0, optimistic=False)
    last_comments = orm.Required(int, default=0, optimistic=False)
    last_local_comments = orm.Required(int, default=0, optimistic=False)
    last_comment_id = orm.Required(int, default=0, optimistic=False)
    last_local_comment_id = orm.Required(int, default=0, optimistic=False)


class StoryLog(db.Entity):
    created_at = orm.Required(datetime, 6, default=datetime.utcnow, index=True)
    user = orm.Optional(Author)
    story = orm.Required(Story)

    chapter_action = orm.Optional(str, 12, py_check=lambda x: x in {'', 'add', 'edit', 'delete'})
    chapter = orm.Optional(Chapter)
    chapter_title = orm.Optional(orm.LongStr, lazy=False)  # На случай, если главу удалят
    # если chapter_action пуст, data_json относится к рассказу, иначе к главе (кроме text)
    data_json = orm.Required(orm.LongStr, lazy=False)  # {key: [old_value, new_value]}
    by_staff = orm.Required(bool, default=False)

    # [["=", длина], ["-", "удалённый кусок"], ["+", "добавленный кусок"]]
    chapter_text_diff = orm.Optional(orm.LongStr, lazy=False)
    chapter_md5 = orm.Optional(str, 32)

    orm.composite_index(story, created_at)
    orm.composite_index(chapter, chapter_md5)
    orm.composite_index(by_staff, created_at)

    @property
    def chapter_autotitle(self):
        if self.chapter_title:
            return self.chapter_title
        if not self.chapter:
            return ''
        if self.chapter.order == 1:
            return self.story.title
        return gettext('Chapter {}').format(self.chapter.order)

    @property
    def data(self):
        return json.loads(self.data_json)


class NewsItem(db.Entity):
    """ Модель новости """

    name = orm.Required(str, 64, index=True, unique=True)
    show = orm.Required(bool, default=False, index=True)
    author = orm.Required(Author)
    title = orm.Required(str, 192)
    content = orm.Optional(orm.LongStr)
    is_template = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    comments_count = orm.Required(int, size=16, unsigned=True, default=0)
    comments = orm.Set('NewsComment')

    bl = Resource('bl.newsitem')

    def __str__(self):
        return self.name

    def before_update(self):
        self.updated = datetime.utcnow()


class NewsComment(db.Entity):
    """ Модель комментария к новости """

    id = orm.PrimaryKey(int, auto=True)
    local_id = orm.Required(int)
    parent = orm.Optional('NewsComment', reverse='answers', nullable=True, default=None)
    author = orm.Optional(Author, nullable=True, default=None)
    author_username = orm.Optional(str, 64)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)
    deleted = orm.Required(bool, default=False)
    last_deleted_at = orm.Optional(datetime, 6, index=True)
    last_deleted_by = orm.Optional(Author)
    newsitem = orm.Required(NewsItem)
    text = orm.Optional(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)
    vote_count = orm.Required(int, size=16, unsigned=True, default=0)
    vote_total = orm.Required(int, default=0)

    # Optimizations
    tree_depth = orm.Required(int, size=16, unsigned=True, default=0)
    answers_count = orm.Required(int, size=16, unsigned=True, default=0)
    edits_count = orm.Required(int, size=16, unsigned=True, default=0)
    root_id = orm.Required(int)  # for pagination
    last_edited_at = orm.Optional(datetime, 6)  # only for text updates
    last_edited_by = orm.Optional(Author)  # only for text updates

    extra = orm.Required(orm.LongStr, lazy=False, default='{}')

    votes = orm.Set('NewsCommentVote')
    edits = orm.Set('NewsCommentEdit')
    answers = orm.Set('NewsComment', reverse='parent')

    bl = Resource('bl.news_comment')

    orm.composite_key(newsitem, local_id)
    orm.composite_index(newsitem, root_id, tree_depth)

    @property
    def brief_text(self):
        return htmlcrop(self.text, current_app.config['BRIEF_COMMENT_LENGTH'])

    text_as_html = filtered_html_property('text', filter_html)
    brief_text_as_html = filtered_html_property('brief_text', filter_html)

    def before_update(self):
        self.updated = datetime.utcnow()


class NewsCommentEdit(db.Entity):
    """ Модель с информацией о редактировании комментария к новости """

    comment = orm.Required(NewsComment)
    editor = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    old_text = orm.Optional(orm.LongStr, lazy=False)
    new_text = orm.Optional(orm.LongStr, lazy=False)
    ip = orm.Required(str, 50, default=ipaddress.ip_address('::1').exploded)


class NewsCommentVote(db.Entity):
    """ Модель голосования за комментарий к новости """

    comment = orm.Required(NewsComment)
    author = orm.Optional(Author)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    vote_value = orm.Required(int, default=0)


class StaticPage(db.Entity):
    name = orm.Required(str, 64)
    lang = orm.Required(str, 6, default='none')
    title = orm.Optional(str, 192)
    content = orm.Optional(orm.LongStr, autostrip=False)
    is_template = orm.Required(bool, default=False)
    is_full_page = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)

    orm.PrimaryKey(name, lang)

    bl = Resource('bl.staticpage')

    def __str__(self):
        if self.name == 'robots.txt':
            label = '/robots.txt'
        else:
            label = '/page/{}/'.format(self.name)
        if self.title:
            label += ' - {}'.format(self.title)
        return label

    def before_update(self):
        self.updated = datetime.utcnow()


class HtmlBlock(db.Entity):
    name = orm.Required(str, 64)
    lang = orm.Required(str, 6, default='none')
    content = orm.Optional(orm.LongStr, autostrip=False)
    is_template = orm.Required(bool, default=False)
    date = orm.Required(datetime, 6, default=datetime.utcnow)
    updated = orm.Required(datetime, 6, default=datetime.utcnow)

    orm.PrimaryKey(name, lang)

    bl = Resource('bl.htmlblock')

    def __str__(self):
        return self.name

    def before_update(self):
        self.updated = datetime.utcnow()


class Notification(db.Entity):
    """Модель уведомления о каком-то событии на сайте.

    Шпаргалка по ныне существующим событиям (в скобках тип, на который
    указывает target_id):

    - story_publish (Story): модератор опубликовал рассказ
    - story_draft (Story): модератор отклонил рассказ
    - author_story (Story): новый рассказ от интересующего автора
    - story_chapter (Chapter): новая глава в рассказе
    - story_reply (StoryComment): ответ на комментарий к рассказу
    - story_comment (StoryComment): не ответ, просто новый комментарий
    - story_lreply (StoryLocalComment): ответ на комментарий в редакторской
    - story_lcomment (StoryLocalComment): новый комментарий в редакторской
    - news_reply (NewsComment): ответ на комментарий к новости
    - news_comment (NewsComment): просто новый комментарий
    - custom (никуда): произвольный HTML-текст
    """
    user = orm.Required(Author)
    created_at = orm.Required(datetime, 6, default=datetime.utcnow)
    type = orm.Required(str, 24, index=True)
    target_id = orm.Optional(int)
    caused_by_user = orm.Optional(Author)
    extra = orm.Required(orm.LongStr, lazy=False, default='{}')


class Subscription(db.Entity):
    """Модель с информацией о подписке на уведомления.

    Куда указывает target_id:
    - author_story: Author
    - story_chapter: Story
    - story_comment: Story
    - story_lcomment: Story
    - news_comment: NewsItem
    """
    user = orm.Required(Author)
    type = orm.Required(str, 24, index=True)
    target_id = orm.Optional(int)
    to_email = orm.Required(bool, default=True)
    to_tracker = orm.Required(bool, default=True)

    orm.composite_index(type, target_id)


class AbuseReport(db.Entity):
    """Жалоба на какой-либо объект:

    - story: на рассказ
    - storycomment: на комментарий к рассказу
    - newscomment: на комментарий к новости
    """

    target_type = orm.Required(str, 24)
    target_id = orm.Required(int)
    user = orm.Optional(Author)
    reason = orm.Required(orm.LongStr, lazy=False)
    created_at = orm.Required(datetime, 6, default=datetime.utcnow)
    updated_at = orm.Required(datetime, 6, default=datetime.utcnow)
    resolved_at = orm.Optional(datetime, 6)
    accepted = orm.Required(bool, default=False)
    ignored = orm.Required(bool, default=False)

    def __str__(self):
        username = self.user.username if self.user else 'N/A'

        if self.target_type == 'story':
            target_obj = Story.get(id=self.target_id)
            target = 'рассказ «{}»'.format(target_obj.title if target_obj else 'N/A')

        elif self.target_type == 'storycomment':
            target_obj = StoryComment.get(id=self.target_id)
            target = 'комментарий {} к рассказу «{}»'.format(
                target_obj.author.username if target_obj.author else (target_obj.author_username or 'N/A'),
                target_obj.story.title,
            )

        elif self.target_type == 'newscomment':
            target_obj = NewsComment.get(id=self.target_id)
            target = 'комментарий {} к новости «{}»'.format(
                target_obj.author.username if target_obj.author else (target_obj.author_username or 'N/A'),
                target_obj.newsitem.name,
            )
        else:
            target = self.target_type + '/' + str(self.target_id)

        return 'Жалоба от {} на {}'.format(username, target)


class AdminLogType(db.Entity):
    """Типы моделей, используемых в истории изменений в админке. Используется
    для составления соответствия id-модель.
    """

    id = orm.PrimaryKey(int, auto=True)
    model = orm.Required(str, 100, unique=True)

    log = orm.Set('AdminLog')


class AdminLog(db.Entity):
    """Лог изменений в админке"""
    # ported from django

    ADDITION = 1
    CHANGE = 2
    DELETION = 3

    action_time = orm.Required(datetime, 6, default=datetime.utcnow)
    user = orm.Optional(Author)
    type = orm.Required(AdminLogType)
    object_id = orm.Required(str, 255)  # str for non-integer pk
    object_repr = orm.Optional(str, 255, autostrip=False)
    action_flag = orm.Required(int, size=8)
    change_message = orm.Optional(orm.LongStr)

    bl = Resource('bl.adminlog')
