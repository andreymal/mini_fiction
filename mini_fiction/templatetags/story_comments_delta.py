#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.templatetags import registry


@registry.simple_tag()
def story_comments_delta(story, author, activity=None):
    return story.comments_count - (activity.last_comments if activity else story.last_comments_by_author(author))
