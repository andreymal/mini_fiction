#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm
from flask import current_app

from mini_fiction.management.manager import manager
from mini_fiction.models import Story, Chapter


def story_check_words_count(story, verbose=True):
    if isinstance(story, int):
        story = Story.get(id=story)
    if not story:
        return

    chapters = list(story.chapters)
    chapters.sort(key=lambda c: c.order)

    all_words = 0
    for chapter in chapters:
        if verbose:
            print('Chapter {}/{} ({}):'.format(chapter.story.id, chapter.order, chapter.id), end=' ', flush=True)

        old_words, new_words = Chapter.bl.update_words_count(chapter, update_story_words=False)
        if verbose:
            print('{} -> {}'.format(old_words, new_words), end='', flush=True)
        all_words += new_words

        if old_words != new_words:
            if verbose:
                print(' (changed)', end='', flush=True)
            orm.commit()
            current_app.tasks['sphinx_update_chapter'].delay(chapter.id, update_story_words=False)

        if verbose:
            print()

    if verbose:
        print('Story {}: {} -> {}'.format(story.id, story.words, all_words), end='', flush=True)

    if story.words != all_words:
        if verbose:
            print(' (changed)', end='', flush=True)
        story.words = all_words
        orm.commit()
        current_app.tasks['sphinx_update_story'].delay(story.id, ('words',))

    if verbose:
        print()


@manager.option('story_ids', metavar='story_ids', nargs='*', default=(), help='Story IDs')
def checkwordscount(story_ids=None):
    orm.sql_debug(False)

    if story_ids:
        for story_id in story_ids:
            with orm.db_session:
                story_check_words_count(int(story_id))
        return

    with orm.db_session:
        first_story = orm.select(orm.min(x.id) for x in Story).first()

    story_id = first_story
    while True:
        with orm.db_session:
            story = Story.select(lambda x: x.id >= story_id).first()
            if not story:
                break
            story_check_words_count(story)
            story_id = story.id + 1
