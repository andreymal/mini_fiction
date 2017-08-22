#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from mini_fiction import ponydump


# Вообще всё будет работать и без этих exclude, но выкидывание избыточной
# информации о связях сильно уменьшает размер дампа
dumpdb_params = {
    'story': {'exclude': (
        'edit_log', 'story_views_set', 'votes', 'favorites', 'bookmarks',
        'comments', 'activity', 'local', 'in_series_permissions',
        'contributors',
    )},
    'author': {'exclude': (
        'activity', 'edit_log',
        'favorites', 'bookmarks', 'contributing', 'coauthorseries',
        'news', 'votes', 'views',
        'news_comments', 'news_comment_edits', 'news_comment_votes',
        'story_comments', 'story_comment_edits', 'story_comment_votes',
        'story_local_comments', 'story_local_comment_edits',
        'contacts', 'subscriptions', 'notifications',
        'created_notifications', 'published_stories', 'approvals',
        'change_email_profiles', 'password_reset_profiles',
        'registration_profile',
    )},
    'chapter': {'exclude': (
        'edit_log', 'chapter_views_set',
    )},
    'storycomment': {'exclude': (
        'answers', 'edits', 'votes',
    )},
    'storylocalthread': {'exclude': (
        'comments',
    )},
    'storylocalcomment': {'exclude': (
        'answers', 'edits',
    )},
    'newsitem': {'exclude': (
        'comments',
    )},
    'newscomment': {'exclude': (
        'answers', 'edits', 'votes',
    )},
    'category': {'exclude': (
        'stories',
    )},
    'character': {'exclude': (
        'stories',
    )},
    'classifier': {'exclude': (
        'stories',
    )},
    'rating': {'exclude': (
        'stories',
    )},
    'series': {'exclude': (
        'permissions',
    )},
}


class MiniFictionDump(ponydump.PonyDump):
    def __init__(self, database=None, dict_params=None, chunk_sizes=None, default_chunk_size=250):
        if database is None:
            from mini_fiction.database import db
            database = db

        ready_dict_params = dict(dumpdb_params)
        if dict_params:
            ready_dict_params.update(dict(dict_params))

        full_chunk_sizes = {
            'chapter': 25,
            'story': 100,
        }
        if chunk_sizes:
            full_chunk_sizes.update(chunk_sizes)

        super().__init__(
            database,
            dict_params=ready_dict_params,
            chunk_sizes=full_chunk_sizes,
            default_chunk_size=default_chunk_size,
        )


def dumpdb_console(dirpath, entities_list=None, gzip_compression=0, progress=True):
    from mini_fiction.utils.misc import progress_drawer

    mfd = MiniFictionDump()

    ljust_cnt = max(len(x) for x in mfd.entities) + 2

    drawer = None
    current = None
    for status in mfd.dump_to_directory(dirpath, entities_list, gzip_compression=gzip_compression):
        if not status['entity']:
            # Закончилось всё
            print()
            continue

        if current != status['entity']:
            current = status['entity']
            if not progress:
                print(current, end='... ')
                sys.stdout.flush()

        if progress and not drawer:
            print(current.ljust(ljust_cnt), end='')
            drawer = progress_drawer(status['count'], show_count=True)
            drawer.send(None)
            drawer.send(status['current'])

        if not status['pk']:
            # Закончилась одна модель
            if progress:
                try:
                    drawer.send(None)
                except StopIteration:
                    pass
                drawer = None
                print()
            else:
                print('ok. {}'.format(status['count']))
            continue

        if progress:
            drawer.send(status['current'])


def loaddb_console(paths, progress=True, only_create=False):
    import os
    from mini_fiction.utils.misc import progress_drawer

    mfd = MiniFictionDump()

    filelist = mfd.walk_all_paths(paths)
    ljust_cnt = max(len(os.path.split(x[1])[-1]) for x in filelist) + 2

    created = 0
    updated = 0
    not_changed = 0

    drawer = None
    current = None
    for statuses in mfd.load_from_files(filelist=filelist, only_create=only_create):
        for status in statuses:
            if status['pk'] is None:
                continue
            if status['created']:
                created += 1
            elif status['updated']:
                updated += 1
            else:
                not_changed += 1

        status = statuses[-1]
        if not status['path']:
            # Закончилось всё
            print()
            continue

        if current != status['path']:
            current = status['path']
            if not progress:
                print(os.path.split(status['path'])[-1], end='... ')
                sys.stdout.flush()

        if progress and not drawer:
            print(os.path.split(status['path'])[-1].ljust(ljust_cnt), end='')
            drawer = progress_drawer(status['count'] or 0, show_count=bool(status['count']))
            drawer.send(None)
            drawer.send(status['current'])

        if not status['entity']:
            # Закончился текущий файл
            if progress:
                try:
                    drawer.send(None)
                except StopIteration:
                    pass
                drawer = None
                print()
            else:
                if status['count'] is not None:
                    print('ok. {}'.format(status['count'] or 0))
                else:
                    print('ok.')
            continue

        if progress:
            drawer.send(status['current'])

    if only_create:
        assert not updated
        print('Finished. {} objects created'.format(created))
    else:
        print('Finished. {} objects created, {} updated, {} not changed'.format(created, updated, not_changed))

    depcache = mfd.get_depcache_dict()
    if depcache:
        print()
        print('WARNING: some optional relations are broken!')
        for k, v in depcache.items():
            print('{}.{} > {}:'.format(k[0][0], k[0][1], k[1][0]))
            for vv in v:
                print('  - {} > {}'.format(
                    vv[0][0] if len(vv[0]) == 1 else vv[0],
                    vv[1][0] if len(vv[1]) == 1 else vv[1],
                ))
