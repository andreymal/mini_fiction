#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.models import Story, StoryContributor, StoryTag, Tag
from mini_fiction.templatetags import registry
from mini_fiction.utils.views import cached_lists


@registry.inclusion_tag('includes/stories_random.html')
def random_stories():
    stories = Story.bl.get_random(prefetch=(
        Story.characters, Story.contributors, StoryContributor.user,
        Story.tags, StoryTag.tag, Tag.category,
    ))
    context = cached_lists([s.id for s in stories], unread_chapters_count=False, unread_comments_count=False)
    context['random_stories'] = stories
    return context
