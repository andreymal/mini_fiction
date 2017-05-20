#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import wraps

from pony.orm import db_session

from mini_fiction.models import Story, Chapter


tasks = {}


def task(name=None, **kwargs):
    def decorator(f):
        tasks[name or f.__name__] = (f, kwargs)
        return f
    return decorator


def task_sphinx_retrying(f):
    @task(bind=True)
    @wraps(f)
    def decorated(self, *args, **kwargs):
        from MySQLdb import OperationalError
        try:
            return f(*args, **kwargs)
        except OperationalError as exc:
            self.retry(countdown=30, max_retries=30, exc=exc)
    return decorated


def apply_for_app(app):
    app.tasks = {}
    for name, (f, kwargs) in tasks.items():
        app.tasks[name] = app.celery.task(**kwargs)(f)


@task(rate_limit='30/m')
@db_session
def sendmail(to, subject, body, fro=None, headers=None, config=None):
    from mini_fiction.utils import mail
    mail.sendmail(to, subject, body, fro=fro, headers=headers, config=config)


@task_sphinx_retrying
@db_session
def sphinx_update_story(story_id, update_fields):
    story = Story.get(id=story_id)
    if not story:
        return

    story.bl.search_update(update_fields)


@task_sphinx_retrying
@db_session
def sphinx_update_chapter(chapter_id):
    chapter = Chapter.get(id=chapter_id)
    if not chapter:
        return

    chapter.bl.search_add()
    chapter.story.bl.search_update(('words',))


@task_sphinx_retrying
@db_session
def sphinx_update_comments_count(story_id):
    story = Story.get(id=story_id)
    if not story:
        return
    story.bl.search_update(('comments',))


@task_sphinx_retrying
def sphinx_delete_story(story_id):
    Story.bl.delete_stories_from_search((story_id,))


@task_sphinx_retrying
@db_session
def sphinx_delete_chapter(story_id, chapter_id):
    Chapter.bl.delete_chapters_from_search((chapter_id,))

    story = Story.get(id=story_id)
    if not story:
        return

    story.bl.search_update(('words',))
