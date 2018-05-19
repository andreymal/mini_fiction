#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm

from mini_fiction.management.manager import manager
from mini_fiction.models import Story, StoryLocalThread, NewsItem


def check_comments_tree(tree, depth=0, root_id=None, parent_id=None):
    for x in tree:
        comment, childtree, _, _ = x
        # Проверка корректности работы get_comments_tree() на всякий случай
        if depth == 0:
            assert comment.parent is None
            assert root_id is None or root_id == comment.id
        else:
            assert comment.parent.id == parent_id
            assert root_id is not None and root_id != comment.id

        # Проверка root_id — id самого первого коммента в ветке (используется в пагинации)
        if depth == 0:
            if comment.root_id != comment.id:
                print(' -{}: root_id {} -> {}'.format(comment.id, comment.root_id, comment.id))
                comment.root_id = comment.id
        else:
            if comment.root_id != root_id:
                print(' -{}: root_id {} -> {}'.format(comment.id, comment.root_id, root_id))
                comment.root_id = root_id

        # Проверка tree_depth
        if comment.tree_depth != depth:
            print(' -{}: depth {} -> {}'.format(comment.id, comment.tree_depth, depth))
            comment.tree_depth = depth

        # Проверка answers_count
        answers_count = comment.answers.select().count()
        if comment.answers_count != answers_count:
            print(' -{}: answers_count {} -> {}'.format(comment.id, comment.answers_count, answers_count))
            comment.answers_count = answers_count

        # Проверка edits_count
        edits_count = comment.edits.select().count()
        if comment.edits_count != edits_count:
            print(' -{}: edits_count {} -> {}'.format(comment.id, comment.edits_count, edits_count))
            comment.edits_count = edits_count

        if hasattr(comment, 'votes'):
            # Проверка vote_count
            vote_count = comment.votes.select().count()
            if comment.vote_count != vote_count:
                print(' -{}: vote_count {} -> {}'.format(comment.id, comment.vote_count, vote_count))
                comment.vote_count = vote_count

            # Проверка vote_total
            vote_total = sum(x.vote_value for x in comment.votes.select()[:])
            if comment.vote_total != vote_total:
                print(' -{}: vote_total {} -> {}'.format(comment.id, comment.vote_total, vote_total))
                comment.vote_total = vote_total

        check_comments_tree(childtree, depth + 1, root_id if depth > 0 else comment.id, comment.id)


def check_comments_for(target, comments_list):
    # Проверяем число комментов
    comments_count = len(comments_list)
    assert comments_count == target.comments.count()
    if hasattr(target, 'comments_count'):
        if target.comments_count != comments_count:
            print('comments_count: {} -> {}'.format(target.comments_count, comments_count))
            target.comments_count = comments_count

    # Перерасчёт local_id
    update_locals = []
    for i, c in enumerate(comments_list, 1):
        if c.local_id != i:
            print(' -{}: #{} -> #{}'.format(c.id, c.local_id, i))
            # Сперва сбрасываем на заведомо несуществующий номер, а то база
            # иногда ругается на неуникальность уникального ключа при исправлении
            c.local_id = -i
            update_locals.append((c, i))
            c.flush()

    # А потом уже расставляем правильные номера
    for c, i in update_locals:
        c.local_id = i
        c.flush()
    del update_locals

    # Проверяем root_id, tree_depth, answers_count,
    # edits_count, vote_count, и vote_total
    # (get_comments_tree() их не использует, так что смело получаем сразу дерево)
    tree = target.bl.get_comments_tree()
    check_comments_tree(tree)


@manager.command
def checkstorycomments():
    orm.sql_debug(False)

    with orm.db_session:
        first_story = orm.select(orm.min(x.id) for x in Story).first()
        last_story = orm.select(orm.max(x.id) for x in Story).first()

    story_id = first_story
    while True:
        with orm.db_session:
            story = Story.select(lambda x: x.id >= story_id and x.id <= last_story).first()
            if not story:
                break

            print('Story {}'.format(story.id))
            comments_list = story.bl.select_comments().order_by('c.date, c.id')

            # Проверка story_published
            pub = story.published
            for c in comments_list:
                if c.story_published != pub:
                    print(' -{}: pub {} -> {}'.format(c.id, c.story_published, pub))
                    c.story_published = pub
                    c.flush()

            # Всё остальное здесь
            check_comments_for(story, comments_list)

            story_id = story.id + 1


@manager.command
def checkstorylocalcomments():
    orm.sql_debug(False)

    with orm.db_session:
        first_local = orm.select(orm.min(x.id) for x in StoryLocalThread).first()
        last_local = orm.select(orm.max(x.id) for x in StoryLocalThread).first()

    local_id = first_local
    while True:
        with orm.db_session:
            local = StoryLocalThread.select(lambda x: x.id >= local_id and x.id <= last_local).first()
            if not local:
                break

            print('Story {} / StoryLocalThread {}'.format(local.story.id, local.id))
            comments_list = local.bl.select_comments().order_by('c.date, c.id')

            # Всё остальное здесь
            check_comments_for(local, comments_list)

            local_id = local.id + 1


@manager.command
def checknewscomments():
    orm.sql_debug(False)

    with orm.db_session:
        first_newsitem = orm.select(orm.min(x.id) for x in NewsItem).first()
        last_newsitem = orm.select(orm.max(x.id) for x in NewsItem).first()

    newsitem_id = first_newsitem
    while True:
        with orm.db_session:
            newsitem = NewsItem.select(lambda x: x.id >= newsitem_id and x.id <= last_newsitem).first()
            if not newsitem:
                break

            print('News item {} ({})'.format(newsitem.id, newsitem.name))
            comments_list = newsitem.bl.select_comments().order_by('c.date, c.id')
            check_comments_for(newsitem, comments_list)

            newsitem_id = newsitem.id + 1
