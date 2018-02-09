#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from pony import orm
from flask import current_app

from mini_fiction.models import Story


def checkstoryvoting():
    if not current_app.story_voting:
        print('Story voting is disabled.')
        return

    with orm.db_session:
        first_story = orm.select(orm.min(x.id) for x in Story).first()
        last_story = orm.select(orm.max(x.id) for x in Story).first()

    story_id = first_story
    while True:
        with orm.db_session:
            story = Story.select(lambda x: x.id >= story_id and x.id <= last_story).first()
            if not story:
                break

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
                print(' (changed)', end='', flush=True)
                orm.commit()
                story.bl.search_update(update_fields={'vote_total', 'vote_value'})
            print()

            story_id = story.id + 1
