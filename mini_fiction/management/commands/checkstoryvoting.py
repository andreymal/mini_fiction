#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import click
from pony import orm
from flask import current_app

from mini_fiction.management.manager import cli
from mini_fiction.models import Story


@cli.command(help='Checks votes of stories.')
@click.argument('story_ids', nargs=-1, type=int)
def checkstoryvoting(story_ids):
    orm.sql_debug(False)

    if not current_app.story_voting:
        print('Story voting is disabled.')
        return

    if not story_ids:
        with orm.db_session:
            first_story = orm.select(orm.min(x.id) for x in Story).first()
            last_story = orm.select(orm.max(x.id) for x in Story).first()
        story_id = first_story
    else:
        story_ids_queue = story_ids[::-1]  # reversed

    while True:
        with orm.db_session:
            if not story_ids:
                stories = Story.select(lambda x: x.id >= story_id and x.id <= last_story).order_by(Story.id)[:50]
                if not stories:
                    break
            else:
                if not story_ids_queue:
                    break
                stories = list(Story.select(lambda x: x.id in story_ids_queue[-50:]).order_by(Story.id))
                story_ids_queue = story_ids_queue[:-50]
                if not stories:
                    continue

            changed_stories = []

            for story in stories:
                print('Story {}:'.format(story.id), end=' ', flush=True)
                old_count = story.vote_total  # TODO: rename to story.vote_count
                old_value = story.vote_value
                old_extra = story.vote_extra

                current_app.story_voting.update_rating(story)

                new_count = story.vote_total
                new_value = story.vote_value
                new_extra = story.vote_extra

                print('{} -> {}'.format(old_value, new_value), end='', flush=True)

                if old_count != new_count or old_value != new_value or json.loads(old_extra) != json.loads(new_extra):
                    print(' (changed)')
                    changed_stories.append(story)
                else:
                    print('')

            print('Saving...', end=' ', flush=True)
            for story in changed_stories:
                story.bl.search_update(update_fields={'vote_total', 'vote_value'})
            orm.commit()
            print('Done.', flush=True)

            if not story_ids:
                story_id = stories[-1].id + 1
