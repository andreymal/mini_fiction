#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=cell-var-from-loop

import sys
import click
from pony import orm

from mini_fiction.management.manager import cli
from mini_fiction.models import Tag, StoryTag, Story


def check_tag_stories_count(verbosity=0):
    last_id = None
    all_count = 0
    changed_count = 0

    while True:
        with orm.db_session:
            tags = Tag.select().order_by(Tag.id)
            if last_id is not None:
                tags = tags.filter(lambda x: x.id > last_id)
            tags = list(tags[:50])
            if not tags:
                break
            last_id = tags[-1].id

            for tag in tags:
                all_count += 1
                changed = False

                data = {
                    'stories_count': StoryTag.select(lambda x: x.tag == tag).count(),
                    'published_stories_count': StoryTag.select(lambda x: x.tag == tag and x.story.published).count(),
                }

                for k, v in data.items():
                    if verbosity >= 2 or v != getattr(tag, k):
                        print('Tag {} (id={}) {}: {} -> {}'.format(
                            tag.name, tag.id, k, getattr(tag, k), v,
                        ), file=sys.stderr)
                    if v != getattr(tag, k):
                        setattr(tag, k, v)
                        changed = True

                if changed:
                    changed_count += 1

    if verbosity >= 1:
        print('{} tags available, {} tags changed'.format(all_count, changed_count), file=sys.stderr)


def check_story_chapters_count(verbosity=0):
    last_id = None
    all_count = 0
    changed_count = 0

    while True:
        with orm.db_session:
            stories = Story.select().order_by(Story.id)
            if last_id is not None:
                stories = stories.filter(lambda x: x.id > last_id)
            stories = list(stories[:50])
            if not stories:
                break
            last_id = stories[-1].id

            for story in stories:
                all_count += 1
                changed = False

                data = {
                    'all_chapters_count': story.chapters.select().count(),
                    'published_chapters_count': story.chapters.select(lambda x: not x.draft).count(),
                }

                for k, v in data.items():
                    if verbosity >= 2 or v != getattr(story, k):
                        print('Story {} {}: {} -> {}'.format(
                            story.id, k, getattr(story, k), v,
                        ), file=sys.stderr)
                    if v != getattr(story, k):
                        setattr(story, k, v)
                        changed = True

                if changed:
                    changed_count += 1

    if verbosity >= 1:
        print('{} stories available, {} stories changed'.format(all_count, changed_count), file=sys.stderr)



@cli.command(short_help='Recalculates counters', help='Recalculates some cached counters (stories count, chapters count etc.)')
@click.option('-m', 'only_modified', help='Print only modified values (less verbose output)', is_flag=True)
def checkcounters(only_modified):
    orm.sql_debug(False)
    check_tag_stories_count(verbosity=1 if only_modified else 2)
    print('', file=sys.stderr)
    check_story_chapters_count(verbosity=1 if only_modified else 2)
