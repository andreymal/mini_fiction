#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from pony import orm
from flask import current_app

from mini_fiction.management.manager import cli
from mini_fiction.models import Story, Chapter


def story_check_words_count(story, verbosity=0):
    if isinstance(story, int):
        story = Story.get(id=story)
    if not story:
        return

    chapters_changed = 0

    chapters = list(story.chapters)
    chapters.sort(key=lambda c: c.order)

    all_words = 0
    for chapter in chapters:
        old_words, new_words = Chapter.bl.update_words_count(chapter, update_story_words=False)
        chapter_changed = old_words != new_words

        if verbosity >= 2 or (verbosity and chapter_changed):
            print(
                f'Chapter {chapter.story.id}/{chapter.order} ({chapter.id}):',
                f'{old_words} -> {new_words}{" (changed)" if chapter_changed else ""}',
            )

        if not chapter.draft:
            all_words += new_words

        if chapter_changed:
            chapters_changed += 1
            orm.commit()
            current_app.tasks['sphinx_update_chapter'].delay(chapter.id, update_story_words=False)

    story_changed = story.words != all_words

    if verbosity >= 2 or (verbosity and story_changed):
        print(
            f'Story {story.id}:',
            f'{story.words} -> {all_words}{" (changed)" if story_changed else ""}',
        )

    if story_changed:
        story.words = all_words
        orm.commit()
        current_app.tasks['sphinx_update_story'].delay(story.id, ('words',))

    return story_changed, chapters_changed


@cli.command(short_help='Recalculates words count.', help='Relalculates words count cache of stories and chapters.')
@click.argument('story_ids', nargs=-1, type=int)
@click.option("-v", "--verbose", "verbosity", count=True, help='Verbosity: -v prints changed items, -vv prints all items.')
def checkwordscount(story_ids, verbosity=0):
    orm.sql_debug(False)

    if story_ids:
        for story_id in story_ids:
            with orm.db_session:
                story_check_words_count(int(story_id), verbosity=verbosity)
        return

    with orm.db_session:
        first_story = orm.select(orm.min(x.id) for x in Story).first()

    story_id = first_story
    while True:
        with orm.db_session:
            story = Story.select(lambda x: x.id >= story_id).first()
            if not story:
                break
            story_check_words_count(story, verbosity=verbosity)
            story_id = story.id + 1
