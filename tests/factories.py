#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hashlib import md5
from datetime import datetime

import factory
from pony import orm

from mini_fiction import models
from mini_fiction.utils.misc import normalize_tag


class PonyFactory(factory.Factory):
    class Meta(object):
        abstract = True

    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        return model_class(*args, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = model_class(*args, **kwargs)
        obj.flush()
        return obj


class AuthorFactory(PonyFactory):
    class Meta(object):
        model = models.Author

    password = ''
    username = factory.Sequence(lambda n: "User%d" % n)
    email = factory.Sequence(lambda n: "user%d@example.com" % n)
    date_joined = factory.LazyAttribute(lambda obj: datetime.utcnow())
    activated_at = factory.LazyAttribute(lambda obj: datetime.utcnow())
    session_token = factory.Sequence(lambda n: "veryrandomtoken%d" % n)


class TagCategoryFactory(PonyFactory):
    class Meta(object):
        model = models.TagCategory

    name = factory.Sequence(lambda n: "Категория %d" % n)


class TagFactory(PonyFactory):
    class Meta(object):
        model = models.Tag

    name = factory.Sequence(lambda n: "Тег %d" % n)
    iname = factory.LazyAttribute(lambda obj: normalize_tag(obj.name))

    @factory.post_generation
    def aliases(self, create, extracted, **kwargs):
        if create and extracted:
            for tag_alias in extracted:
                TagFactory(name=tag_alias, is_alias_for=self)


class StoryFactory(PonyFactory):
    class Meta(object):
        model = models.Story

    title = factory.Sequence(lambda n: "Story %d" % n)
    rating = factory.LazyAttribute(lambda obj: models.Rating.select().first())
    summary = factory.Sequence(lambda n: "This is best story %d" % n)
    draft = False
    approved = True
    first_published_at = factory.LazyAttribute(lambda obj: datetime.utcnow())

    @factory.post_generation
    def betas(self, create, extracted, **kwargs):
        if create and extracted:
            for user in extracted:
                StoryBetaUserFactory(story=self, user=user)

    @factory.post_generation
    def editors(self, create, extracted, **kwargs):
        if create and extracted:
            for user in extracted:
                StoryEditorUserFactory(story=self, user=user)

    @factory.post_generation
    def authors(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted is None:
            StoryCoauthorUserFactory(story=self)
            return

        for user in extracted:
            StoryCoauthorUserFactory(story=self, user=user)


class DraftStoryFactory(StoryFactory):
    draft = True
    approved = False
    first_published_at = None


class StoryContributorFactory(PonyFactory):
    class Meta(object):
        model = models.StoryContributor

    story = factory.SubFactory(StoryFactory)
    user = factory.SubFactory(AuthorFactory)


class StoryBetaUserFactory(StoryContributorFactory):
    is_editor = False
    is_author = False


class StoryEditorUserFactory(StoryContributorFactory):
    is_editor = True
    is_author = False


class StoryCoauthorUserFactory(StoryContributorFactory):
    is_editor = True
    is_author = True
    visible = True


class StoryBadCoauthorUserFactory(StoryContributorFactory):
    is_editor = False
    is_author = True
    visible = True


class ChapterFactory(PonyFactory):
    class Meta(object):
        model = models.Chapter

    story = factory.SubFactory(StoryFactory)
    order = factory.LazyAttribute(
        lambda obj: (orm.select(orm.max(x.order) for x in models.Chapter if x.story == obj.story).first() or 0) + 1
    )
    text = factory.Sequence(lambda n: "This is text of chapter %d" % n)
    text_md5 = factory.LazyAttribute(lambda obj: md5(obj.text.encode('utf-8')).hexdigest())
    story_published = factory.LazyAttribute(lambda obj: obj.story.published)
    first_published_at = factory.LazyAttribute(lambda obj: None if obj.draft else obj.story.first_published_at)
    draft = False
