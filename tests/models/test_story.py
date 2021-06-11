#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name,unused-variable

import pytest
from pony import orm

from mini_fiction import models


@pytest.mark.nodbcleaner
def test_story_deletion_full(app, factories):
    def _check_db_is_empty():
        # Эти фикстуры всегда на месте
        assert models.CharacterGroup.select().count() == 1
        assert models.Character.select().count() == 1
        # assert models.Category.select().count() == 1
        # assert models.Classifier.select().count() == 1
        assert models.Tag.select().count() == 1
        assert models.Rating.select().count() == 4

        assert models.Author.select().count() == 4  # moderator, author, reader, system

        # А тут уже всё связанное с рассказом, что должно удаляться
        assert models.Story.select().count() == 0
        assert models.StoryTag.select().count() == 0
        assert models.StoryTagLog.select().count() == 0
        assert models.StoryContributor.select().count() == 0
        assert models.Chapter.select().count() == 0
        assert models.StoryLog.select().count() == 0
        assert models.StoryView.select().count() == 0
        assert models.Activity.select().count() == 0
        assert models.Vote.select().count() == 0

        assert models.StoryComment.select().count() == 0
        assert models.StoryCommentEdit.select().count() == 0
        assert models.StoryCommentVote.select().count() == 0

        assert models.StoryLocalThread.select().count() == 0
        assert models.StoryLocalComment.select().count() == 0
        assert models.StoryLocalCommentEdit.select().count() == 0

        assert models.Favorites.select().count() == 0
        assert models.Bookmark.select().count() == 0
        assert models.Subscription.select().count() == 0
        assert models.Notification.select().count() == 0

    with orm.db_session:
        # Фикстуры
        cg = models.CharacterGroup(name='Main')
        cg.flush()
        models.Character(name='Даша', group=cg).flush()
        # models.Category(name='Приключения').flush()
        # models.Classifier(name='Особо жестокие сцены').flush()
        models.Tag(name='Приключения', iname='приключения').flush()

        moderator = factories.AuthorFactory(username='Moderator', is_staff=True)
        author = factories.AuthorFactory(username='Author')
        reader = factories.AuthorFactory(username='Reader')

        # Проверяем, что перед тестом БД пустая (кроме фикстур)
        _check_db_is_empty()

        # Создаём сам рассказ
        story = factories.StoryFactory(authors=[author])
        chapter1 = factories.ChapterFactory(story=story)
        chapter2 = factories.ChapterFactory(story=story)

        story.characters.add(models.Character.select().first())
        # story.categories.add(models.Category.select().first())
        # story.classifications.add(models.Classifier.select().first())
        story.bl.set_tags(author, ['Приключения'], log=True, update_search=False)

        lt = models.StoryLocalThread(story=story)
        lt.flush()

        # Создаём как можно больше связей с рассказом для проверки
        # корректности удаления:

        # Модератор опубликовал рассказ
        models.StoryLog(
            story=story, user=moderator, by_staff=True,
            data_json='{"approved": [false, true]}', created_at=story.first_published_at,
        ).flush()

        # но оставил пару замечаний
        lc1 = models.StoryLocalComment(
            local_id=1, author=moderator, author_username=moderator.username,
            local=lt, text='Расставить запятые, нельзя убрать', root_id=0,
            edits_count=1, answers_count=1,
            tree_depth=0,
        )
        lc1.flush()
        lc1.root_id = lc1.id

        # Упс
        models.StoryLocalCommentEdit(
            comment=lc1, editor=reader,
            old_text='Расставить запятые нельзя убрать', new_text='Расставить запятые, нельзя убрать',
        )

        # Автор поредактировал главу
        models.StoryLog(
            story=story, user=author, chapter=chapter1, chapter_title=chapter1.title,
            chapter_text_diff='[["=", {}]]'.format(len(chapter1.text)),
            chapter_md5=chapter1.text_md5, data_json='{}',
        ).flush()

        # и докладывает модератору
        lc2 = models.StoryLocalComment(
            local_id=2, author=author, author_username=author.username,
            local=lt, text='fxd', parent=lc1, root_id=lc1.id,
            tree_depth=1,
        )
        lc2.flush()

        # Читатель почитал рассказ
        models.StoryView(author=reader, story=story, chapter=chapter1).flush()
        models.StoryView(author=reader, story=story, chapter=chapter2).flush()
        models.Activity(author=reader, story=story).flush()

        # и он ему очень понравился
        models.Vote(author=reader, story=story, vote_value=5).flush()

        # о чём он спешит сообщить автору
        c1 = models.StoryComment(
            local_id=1, author=reader, author_username=reader.username,
            story=story, text='Прекрасный рассказ!', root_id=0,
            story_published=story.published,
            vote_count=1, vote_total=1, edits_count=1, answers_count=1,
            tree_depth=0,
        )
        c1.flush()
        c1.root_id = c1.id

        # Так спешил, что опечатался
        models.StoryCommentEdit(
            comment=c1, editor=reader,
            old_text='Пекрасный рассказ!', new_text='Прекрасный рассказ!',
        )

        # Автора радует этот комментарий
        models.StoryCommentVote(comment=c1, author=author, vote_value=1)

        # И он благодарит читателя за него
        c2 = models.StoryComment(
            local_id=2, author=author, author_username=author.username,
            story=story, text='Спасибо!', parent=c1, root_id=c1.id,
            story_published=story.published,
            tree_depth=1,
        )
        c2.flush()

        # Рассказ, естественно, в избранном, в закладках и в подписках
        models.Bookmark(story=story, author=reader).flush()
        models.Favorites(story=story, author=reader).flush()
        models.Subscription(user=reader, type='story_chapter', target_id=story.id).flush()

        # Немного уведомлений уже тоже было
        models.Notification(user=author, caused_by_user=moderator, type='story_publish', target_id=story.id).flush()
        models.Notification(user=reader, caused_by_user=author, type='story_chapter', target_id=chapter2.id).flush()
        models.Notification(user=author, caused_by_user=reader, type='story_comment', target_id=c1.id).flush()
        models.Notification(user=reader, caused_by_user=author, type='story_reply', target_id=c2.id).flush()

        story_id = story.id

    try:
        # Но что-то в жизни автора пошло не так...
        # И он захотел удалить столь прекрасный рассказ!
        # Что ж, его право.
        with orm.db_session:
            models.Story.get(id=story_id).bl.delete(user=author)

        # На данный момент поля Story.deleted не существует, и рассказ должен
        # просто вычищаться из базы целиком и полностью
        with orm.db_session:
            _check_db_is_empty()

    finally:
        # Database Cleaner отключен в этом тесте, чистим остатки сами
        with orm.db_session:
            models.Character.select().delete()
            models.CharacterGroup.select().delete()
            #models.Category.select().delete()
            #models.Classifier.select().delete()
            models.Tag.select().delete()

        try:
            # Если тест упал, то и это иногда падает, эх
            with orm.db_session:
                models.Author.select(lambda x: x.id >= 0).delete()
        except Exception as exc:
            print('Cannot clean authors: {}'.format(exc))
