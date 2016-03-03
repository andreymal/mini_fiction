#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pony.orm import db_session

from mini_fiction.models import Story, Chapter


tasks = {}


def task(f, name=None, **kwargs):
    tasks[name or f.__name__] = (f, kwargs)
    return f


def apply_for_app(app):
    app.tasks = {}
    for name, (f, kwargs) in tasks.items():
        app.tasks[name] = app.celery.task(**kwargs)(f)


@task
@db_session
def sphinx_update_story(story_id, update_fields):
    story = Story.get(id=story_id)
    if not story:
        return

    story.bl.search_update(update_fields)


@task
@db_session
def sphinx_update_chapter(chapter_id):
    chapter = Chapter.get(id=chapter_id)
    if not chapter:
        return

    chapter.bl.search_add()
    chapter.story.bl.search_update(('words',))


@task
@db_session
def sphinx_update_comments_count(story_id):
    story = Story.get(id=story_id)
    if not story:
        return
    story.bl.search_update(('comments',))


@task
def sphinx_delete_story(story_id):
    Story.bl.delete_stories_from_search((story_id,))


@task
@db_session
def sphinx_delete_chapter(story_id, chapter_id):
    Chapter.bl.delete_chapters_from_search((chapter_id,))

    story = Story.get(id=story_id)
    if not story:
        return

    story.bl.search_update(('words',))
