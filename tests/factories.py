#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

import factory

from mini_fiction import models


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
    username = factory.Sequence(lambda n: "user%d" % n)
    email = factory.Sequence(lambda n: "user%d@example.com" % n)
    date_joined = factory.LazyAttribute(lambda obj: datetime.utcnow())
