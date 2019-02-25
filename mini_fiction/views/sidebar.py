#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import select
from flask import current_app, render_template
from flask_login import current_user

from mini_fiction.utils.views import cached_lists
from mini_fiction.models import Chapter, Story, StoryContributor, StoryComment, NewsComment, NewsItem


def chapters_updates(params):
    # Старая логика, при которой могли выводиться много глав одного рассказа подряд
    # chapters = select(c for c in Chapter if not c.draft and c.story_published and c.order != 1)
    # chapters = chapters.order_by(Chapter.first_published_at.desc(), Chapter.order.desc())
    # chapters = chapters[:current_app.config['CHAPTERS_COUNT']['main']]
    # story_ids = [y.story.id for y in chapters]
    # chapters_stories = select(x for x in Story if x.id in story_ids).prefetch(Story.contributors, StoryContributor.user)[:]
    # chapters_stories = {x.id: x for x in chapters_stories}
    # chapters = [(x, chapters_stories[x.story.id]) for x in chapters]

    chapters = current_app.cache.get('index_updated_chapters')
    if chapters is None:
        # Забираем id последних обновлённых рассказов
        # (главы не берём, так как у одного рассказа их может быть много, а нам нужна всего одна)
        index_updated_story_ids = select((c.story.id, max(c.first_published_at)) for c in Chapter if not c.draft and c.story_published and c.order != 1)
        index_updated_story_ids = [x[0] for x in index_updated_story_ids.order_by(-2)[:current_app.config['CHAPTERS_COUNT']['main']]]

        # Забираем последнюю главу каждого рассказа
        # (TODO: наверняка можно оптимизировать, но не придумалось как)
        latest_chapters = list(select(
            (c.story.id, c.id, c.first_published_at, c.order)
            for c in Chapter
            if not c.draft and c.story_published and c.story.id in index_updated_story_ids
        ).order_by(-3, -4))

        index_updated_chapter_ids = []
        for story_id in index_updated_story_ids:
            for x in latest_chapters:
                if x[0] == story_id:
                    index_updated_chapter_ids.append(x[1])
                    break
        assert len(index_updated_chapter_ids) == len(index_updated_story_ids)

        chapters_objs = Chapter.select(lambda x: x.id in index_updated_chapter_ids)
        chapters_objs = {x.id: x for x in chapters_objs.prefetch(Chapter.story, Story.contributors, StoryContributor.user)}

        # Переводим в более простой формат, близкий к json, чтоб удобнее кэшировать и задел на будущие переделки
        # И попутно сортировка
        chapters = []
        for chapter_id in index_updated_chapter_ids:
            x = chapters_objs[chapter_id]
            chapters.append({
                'id': x.id,
                'order': x.order,
                'title': x.title,
                'autotitle': x.autotitle,
                'first_published_at': x.first_published_at,
                'story': {
                    'id': x.story.id,
                    'title': x.story.title,
                    'first_published_at': x.story.first_published_at,
                    'updated': x.story.updated,
                    'authors': [{
                        'id': a.id,
                        'username': a.username,
                    } for a in x.story.authors]
                }
            })
        current_app.cache.set('index_updated_chapters', chapters, 600)

    # Число непрочитанных глав у текущего пользователя
    if current_user.is_authenticated:
        unread_chapters_count = Story.bl.get_unread_chapters_count(
            current_user._get_current_object(), [x['story']['id'] for x in chapters]
        )
    else:
        unread_chapters_count = {x['story']['id']: 0 for x in chapters}

    return render_template('sidebar/chapters_updates.html', chapters=chapters, unread_chapters_count=unread_chapters_count)


def comments_updates(params):
    comments_html = None
    if not current_user.is_authenticated:
        comments_html = current_app.cache.get('index_comments_html_guest')

    if not comments_html:
        # Старая логика, при которой могли появляться несколько комментариев одной сущности

        # story_comments = StoryComment.select(lambda x: x.story_published and not x.deleted).order_by(StoryComment.id.desc())
        # story_comments = story_comments[:current_app.config['COMMENTS_COUNT']['main']]

        # news_comments = NewsComment.select(lambda x: not x.deleted).order_by(NewsComment.id.desc())
        # news_comments = news_comments[:current_app.config['COMMENTS_COUNT']['main']]

        stories = select(x for x in Story if x.published and x.last_comment_id > 0).order_by(Story.last_comment_id.desc())[:current_app.config['COMMENTS_COUNT']['main']]
        story_comment_ids = [x.last_comment_id for x in stories]
        story_comments = StoryComment.select(lambda x: x.id in story_comment_ids).order_by(StoryComment.id.desc())[:current_app.config['COMMENTS_COUNT']['main']]

        news_list = select(x for x in NewsItem if x.last_comment_id > 0).order_by(NewsItem.last_comment_id.desc())[:current_app.config['COMMENTS_COUNT']['main']]
        news_comment_ids = [x.last_comment_id for x in news_list]
        news_comments = NewsComment.select(lambda x: x.id in news_comment_ids).order_by(NewsComment.id.desc())[:current_app.config['COMMENTS_COUNT']['main']]

        comments = [('story', x) for x in story_comments]
        comments += [('news', x) for x in news_comments]
        comments.sort(key=lambda x: x[1].date, reverse=True)
        comments = comments[:current_app.config['COMMENTS_COUNT']['main']]

        data = dict(
            comments=comments,
            comments_short=True,
        )

        # Для счётчика непрочитанных комментариев
        data.update(cached_lists([x.id for x in stories]))

        comments_html = render_template(
            'includes/comments_list.html',
            **data
        )

        if not current_user.is_authenticated:
            current_app.cache.set('index_comments_html_guest', comments_html, 3600)

    return render_template('sidebar/comments_updates.html', comments_html=comments_html)


def news(params):
    news_list = list(NewsItem.select().order_by(NewsItem.id.desc())[:3])
    return render_template('sidebar/news.html', news=news_list)
