#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.models import Story
from mini_fiction.templatetags import registry


@registry.simple_tag()
def submitted_stories_count():
    return Story.select_submitted().count()
