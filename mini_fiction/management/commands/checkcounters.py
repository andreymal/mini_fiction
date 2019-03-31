#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=cell-var-from-loop

import sys
import click
from pony import orm

from mini_fiction.management.manager import cli
from mini_fiction.models import Tag, StoryTag, Story, Chapter, StoryView


def check_tag_stories_count(verbosity=0, dry_run=False):
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
                    if verbosity >= 2 or (verbosity and v != getattr(tag, k)):
                        print('Tag {} (id={}) {}: {} -> {}'.format(
                            tag.name, tag.id, k, getattr(tag, k), v,
                        ), file=sys.stderr)
                    if v != getattr(tag, k):
                        if not dry_run:
                            setattr(tag, k, v)
                        changed = True

                if changed:
                    changed_count += 1

    if verbosity >= 1:
        print('{} tags available, {} tags changed'.format(all_count, changed_count), file=sys.stderr)


def check_story_chapters_and_views_count(verbosity=0, dry_run=False):
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

                views = set(orm.select(x.author.id for x in StoryView if x.story == story))

                data = {
                    'all_chapters_count': story.chapters.select().count(),
                    'published_chapters_count': story.chapters.select(lambda x: not x.draft).count(),
                    'views': len(views),
                }

                for k, v in data.items():
                    if verbosity >= 2 or (verbosity and v != getattr(story, k)):
                        print('Story {} {}: {} -> {}'.format(
                            story.id, k, getattr(story, k), v,
                        ), file=sys.stderr)
                    if v != getattr(story, k):
                        if not dry_run:
                            setattr(story, k, v)
                        changed = True

                if changed:
                    changed_count += 1

    if verbosity >= 1:
        print('{} stories available, {} stories changed'.format(all_count, changed_count), file=sys.stderr)


def check_chapter_views_count(verbosity=0, dry_run=False):
    last_id = None
    all_count = 0
    changed_count = 0

    while True:
        with orm.db_session:
            chapters = Chapter.select().order_by(Chapter.id)
            if last_id is not None:
                chapters = chapters.filter(lambda x: x.id > last_id)
            chapters = list(chapters[:150])
            if not chapters:
                break
            last_id = chapters[-1].id

            for chapter in chapters:
                all_count += 1
                changed = False

                views = set(orm.select(x.author.id for x in StoryView if x.chapter == chapter))

                data = {
                    'views': len(views),
                }

                for k, v in data.items():
                    if verbosity >= 2 or (verbosity and v != getattr(chapter, k)):
                        print('Chapter {}/{} ({}) {}: {} -> {}'.format(
                            chapter.story.id, chapter.order, chapter.id, k, getattr(chapter, k), v,
                        ), file=sys.stderr)
                    if v != getattr(chapter, k):
                        if not dry_run:
                            setattr(chapter, k, v)
                        changed = True

                if changed:
                    changed_count += 1

    if verbosity >= 1:
        print('{} chapters available, {} chapters changed'.format(all_count, changed_count), file=sys.stderr)


@cli.command(short_help='Recalculates counters', help='Recalculates some cached counters (stories count, chapters count, views etc.)')
@click.option('-m', 'only_modified', help='Print only modified values (less verbose output)', is_flag=True)
@click.option('-d', '--dry-run', 'dry_run', help='Only print log with no changes made', is_flag=True)
def checkcounters(only_modified, dry_run):
    orm.sql_debug(False)

    verbosity = 1 if only_modified else 2

    check_tag_stories_count(verbosity=verbosity, dry_run=dry_run)
    if verbosity:
        print('', file=sys.stderr)
    check_story_chapters_and_views_count(verbosity=verbosity, dry_run=dry_run)
    if verbosity:
        print('', file=sys.stderr)
    check_chapter_views_count(verbosity=verbosity, dry_run=dry_run)

    if verbosity and dry_run:
        print('', file=sys.stderr)
        print('(DRY RUN)', file=sys.stderr)
