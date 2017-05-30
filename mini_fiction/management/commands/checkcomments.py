#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm

from mini_fiction.models import Story, NewsItem


def check_comments_tree(tree, depth=0, root_order=0, parent_id=None):
    for i, x in enumerate(tree):
        comment, childtree, _, _ = x
        # Проверка корректности работы get_comments_tree() на всякий случай
        if depth == 0:
            assert comment.parent is None
        else:
            assert comment.parent.id == parent_id

        # Проверка root_order (используется в пагинации)
        if depth == 0:
            if comment.root_order != i:
                print(' -{}: root_order {} -> {}'.format(comment.id, comment.root_order, i))
                comment.root_order = i
        else:
            if comment.root_order != root_order:
                print(' -{}: root_order {} -> {}'.format(comment.id, comment.root_order, root_order))
                comment.root_order = root_order

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

        check_comments_tree(childtree, depth + 1, root_order if depth > 0 else i, comment.id)


def check_comments_for(target, comments_list):
    # Проверяем число комментов
    comments_count = len(comments_list)
    assert comments_count == target.comments.count()
    if hasattr(target, 'comments_count'):
        if target.comments_count != comments_count:
            print('comments_count: {} -> {}'.format(target.comments_count, comments_count))
            target.comments_count = comments_count

    # Перерасчёт local_id
    for i, c in enumerate(comments_list, 1):
        if c.local_id != i:
            print(' -{}: #{} -> #{}'.format(c.id, c.local_id, i))
            c.local_id = i
            c.flush()

    # Проверяем root_order, tree_depth, answers_count,
    # edits_count, vote_count, и vote_total
    # (get_comments_tree() их не использует, так что смело получаем сразу дерево)
    tree = target.bl.get_comments_tree()
    check_comments_tree(tree)


def checkstorycomments():
    first_story = orm.select(orm.min(x.id) for x in Story).first()
    last_story = orm.select(orm.max(x.id) for x in Story).first()

    story_id = first_story
    while True:
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


def checknewscomments():
    first_newsitem = orm.select(orm.min(x.id) for x in NewsItem).first()
    last_newsitem = orm.select(orm.max(x.id) for x in NewsItem).first()

    newsitem_id = first_newsitem
    while True:
        newsitem = NewsItem.select(lambda x: x.id >= newsitem_id and x.id <= last_newsitem).first()
        if not newsitem:
            break

        print('News item {} ({})'.format(newsitem.id, newsitem.name))
        comments_list = newsitem.bl.select_comments().order_by('c.date, c.id')
        check_comments_for(newsitem, comments_list)

        newsitem_id = newsitem.id + 1
