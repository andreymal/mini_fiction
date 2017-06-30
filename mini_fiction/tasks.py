#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import wraps

import json
from flask import current_app
from pony.orm import db_session

from mini_fiction import models
from mini_fiction.models import Story, Chapter
from mini_fiction.utils.misc import render_nonrequest_template


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


# common tasks


@task(rate_limit='30/m')
def sendmail(to, subject, body, fro=None, headers=None, config=None):
    from mini_fiction.utils import mail
    mail.sendmail(to, subject, body, fro=fro, headers=headers, config=config)


# search updating tasks


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


# tasks for notificaions


def _sendmail_notify(to, typ, ctx):
    if not to:
        return
    if not isinstance(to, (list, set, tuple)):
        to = [to]

    kwargs = {
        'to': list(to),
        'subject': render_nonrequest_template('email/{}_subject.txt'.format(typ), **ctx),
        'body': {
            'plain': render_nonrequest_template('email/{}.txt'.format(typ), **ctx),
            'html': render_nonrequest_template('email/{}.html'.format(typ), **ctx),
        },
    }

    return current_app.tasks['sendmail'].delay(**kwargs)


def _notify(to, typ, target, by=None, extra=None):
    if not to:
        return []
    if not isinstance(to, (list, set, tuple)):
        to = [to]

    result = []
    for x in to:
        result.append(models.Notification(
            user=x,
            type=typ,
            target_id=target.id,
            caused_by_user=by,
            extra=json.dumps(extra or {}, ensure_ascii=False, sort_keys=True),
        ))
        current_app.cache.delete('bell_{}'.format(x.id))
    return result


@task()
@db_session
def notify_story_pubrequest(story_id, author_id):
    story = models.Story.get(id=story_id)
    if not story:
        return
    author = models.Author.get(id=author_id)
    if not author:
        return

    staff = models.Author.select(lambda x: x.is_staff)
    recipients = [u.email for u in staff if u.email and 'story_pubrequest' not in u.silent_email_list]
    _sendmail_notify(recipients, 'story_pubrequest', {'story': story, 'author': author})


@task()
@db_session
def notify_story_publish_draft(story_id, staff_id, draft):
    story = models.Story.get(id=story_id)
    if not story:
        return

    author = story.published_by_author
    staff = models.Author.get(id=staff_id)
    if not author or not staff:
        return

    typ = 'story_draft' if draft else 'story_publish'

    if typ not in author.silent_tracker_list:
        _notify(author, typ, story, by=staff)

    if author.email and typ not in author.silent_email_list:
        _sendmail_notify([author.email], typ, {'story': story, 'author': author, 'staff': staff})


@task()
@db_session
def notify_story_chapters(chapter_ids, publisher_user_id=None):
    # Получаем главы и проверяем адекватность
    chapters = models.Chapter.select(lambda x: x.id in chapter_ids)[:]
    if not chapters:
        return
    story = chapters[0].story
    for c in chapters[1:]:
        assert c.story == story

    chapters.sort(key=lambda x: x.order)

    # Получаем подписчиков, ждущих главы
    subs = models.Subscription.select(lambda x: x.type == 'story_chapter' and x.target_id == story.id)[:]

    sendto = set()  # Список почт для отправки

    # Перебираем все подписки
    for sub in subs:
        user = sub.user

        # Если этот юзер и опубликовал главы, то его уведомлять не надо
        if user.id == publisher_user_id:
            continue

        # Если есть подписка на сайте, создаём уведомление
        if sub.to_tracker:
            for c in chapters:
                _notify(user, 'story_chapter', c)

        # Если есть подписка на почту, забираем адрес для последующей отправки
        if sub.to_email and user.email:
            sendto.add(user.email)

    # Отправляем письмо по собранным адресам
    _sendmail_notify(sendto, 'story_chapter', {'story': story, 'chapters': chapters})

@task()
@db_session
def notify_story_comment(comment_id):
    comment = models.StoryComment.get(id=comment_id)
    if not comment:
        return
    story = comment.story
    parent = comment.parent

    ctx = {'story': story, 'comment': comment, 'parent': parent}

    reply_sent_email = False
    reply_sent_tracker = False

    if parent and parent.author and (not comment.author or parent.author.id != comment.author.id):
        # Уведомляем автора родительского комментария, что ему ответили
        if 'story_reply' not in parent.author.silent_tracker_list:
            _notify(parent.author, 'story_reply', comment, by=comment.author)
            reply_sent_tracker = True

        if 'story_reply' not in parent.author.silent_email_list and parent.author.email:
            _sendmail_notify([parent.author.email], 'story_reply', ctx)
            reply_sent_email = True

    # Уведомляем остальных подписчиков о появлении нового комментария
    subs = models.Subscription.select(lambda x: x.type == 'story_comment' and x.target_id == story.id)[:]

    sendto = set()
    for sub in subs:
        user = sub.user
        if comment.author and user.id == comment.author.id:
            continue

        # Не забываем про проверку доступа
        if not story.bl.has_access(user):
            continue

        if sub.to_tracker:
            if not parent or not parent.author or parent.author.id != user.id or not reply_sent_tracker:
                _notify(user, 'story_comment', comment, by=comment.author)

        if sub.to_email and user.email:
            if not parent or not parent.author or parent.author.id != user.id or not reply_sent_email:
                sendto.add(user.email)

    _sendmail_notify(sendto, 'story_comment', ctx)


@task()
@db_session
def notify_story_lcomment(comment_id):
    comment = models.StoryLocalComment.get(id=comment_id)
    if not comment:
        return
    story = comment.local.story
    parent = comment.parent

    ctx = {'story': story, 'comment': comment, 'parent': parent}

    # Достаём информацию, кем является автор комментария
    contributor = story.contributors.select(lambda x: x.user == comment.author).first()
    if contributor:
        extra = {'is_editor': contributor.is_editor, 'is_author': contributor.is_author, 'is_staff': comment.author.is_staff}
    elif comment.author and comment.author.is_staff:
        extra = {'is_editor': False, 'is_author': False, 'is_staff': True}
    else:
        extra = {'is_editor': False, 'is_author': False, 'is_staff': False, 'unknown': True}
    ctx.update(extra)

    reply_sent_email = False
    reply_sent_tracker = False

    if parent and parent.author and (not comment.author or parent.author.id != comment.author.id):
        # Уведомляем автора родительского комментария, что ему ответили
        if 'story_lreply' not in parent.author.silent_tracker_list:
            _notify(parent.author, 'story_lreply', comment, by=comment.author, extra=extra)
            reply_sent_tracker = True

        if 'story_lreply' not in parent.author.silent_email_list and parent.author.email:
            _sendmail_notify([parent.author.email], 'story_lreply', ctx)
            reply_sent_email = True

    # Уведомляем остальных подписчиков о появлении нового комментария
    subs = models.Subscription.select(lambda x: x.type == 'story_lcomment' and x.target_id == story.id)[:]

    sendto = set()
    for sub in subs:
        user = sub.user
        if comment.author and user.id == comment.author.id:
            continue

        # Не забываем про проверку доступа
        if not user.is_staff and not story.bl.is_contributor(user):
            continue

        if sub.to_tracker:
            if not parent or not parent.author or parent.author.id != user.id or not reply_sent_tracker:
                _notify(user, 'story_lcomment', comment, by=comment.author, extra=extra)

        if sub.to_email and user.email:
            if not parent or not parent.author or parent.author.id != user.id or not reply_sent_email:
                sendto.add(user.email)

    _sendmail_notify(sendto, 'story_lcomment', ctx)


@task()
@db_session
def notify_news_comment(comment_id):
    comment = models.NewsComment.get(id=comment_id)
    if not comment:
        return
    newsitem = comment.newsitem
    parent = comment.parent

    ctx = {'newsitem': newsitem, 'comment': comment, 'parent': parent}

    reply_sent_email = False
    reply_sent_tracker = False

    if parent and parent.author and (not comment.author or parent.author.id != comment.author.id):
        # Уведомляем автора родительского комментария, что ему ответили
        if 'news_reply' not in parent.author.silent_tracker_list:
            _notify(parent.author, 'news_reply', comment, by=comment.author)
            reply_sent_tracker = True

        if 'news_reply' not in parent.author.silent_email_list and parent.author.email:
            _sendmail_notify([parent.author.email], 'news_reply', ctx)
            reply_sent_email = True

    # Уведомляем остальных подписчиков о появлении нового комментария
    subs = models.Subscription.select(lambda x: x.type == 'news_comment' and x.target_id == newsitem.id)[:]

    sendto = set()
    for sub in subs:
        user = sub.user
        if comment.author and user.id == comment.author.id:
            continue

        if sub.to_tracker:
            if not parent or not parent.author or parent.author.id != user.id or not reply_sent_tracker:
                _notify(user, 'news_comment', comment, by=comment.author)

        if sub.to_email and user.email:
            if not parent or not parent.author or parent.author.id != user.id or not reply_sent_email:
                sendto.add(user.email)

    _sendmail_notify(sendto, 'news_comment', ctx)
