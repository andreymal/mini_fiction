#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.models import Story, StoryContributor, StoryTag, Tag
from mini_fiction.templatetags import registry


@registry.inclusion_tag('includes/stories_random.html')
def random_stories():
    stories = Story.bl.get_random(prefetch=(
        Story.characters, Story.contributors, StoryContributor.user,
        Story.tags, StoryTag.tag, Tag.category,
    ))
    return {'random_stories': stories}


@registry.inclusion_tag('experimental/includes/stories_random.html')
def experimental_random_stories():
    stories = Story.bl.get_random(prefetch=(
        Story.characters, Story.contributors, StoryContributor.user,
        Story.tags, StoryTag.tag, Tag.category,
    ))
    return {'random_stories': stories}
