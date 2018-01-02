#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony import orm

from mini_fiction.models import Chapter


def checkwordscount():
    with orm.db_session:
        first_chapter = orm.select(orm.min(x.id) for x in Chapter).first()
        last_chapter = orm.select(orm.max(x.id) for x in Chapter).first()

    chapter_id = first_chapter
    while True:
        with orm.db_session:
            chapter = Chapter.select(lambda x: x.id >= chapter_id and x.id <= last_chapter).prefetch(Chapter.story).first()
            if not chapter:
                break

            print('Chapter {}/{} ({}):'.format(chapter.story.id, chapter.order, chapter.id), end=' ', flush=True)
            old_words, new_words = Chapter.bl.update_words_count(chapter)
            print('{} -> {}'.format(old_words, new_words), end='', flush=True)

            if old_words != new_words:
                print(' (changed)', end='', flush=True)
                orm.commit()
            print()

            chapter_id = chapter.id + 1
