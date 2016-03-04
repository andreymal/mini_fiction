#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, render_template, abort, url_for, redirect
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.forms.chapter import ChapterForm
from mini_fiction.models import Story, Chapter
from .story import get_story

bp = Blueprint('chapter', __name__)


@bp.route('/story/<int:story_id>/chapter/all/', defaults={'chapter_order': None})
@bp.route('/story/<int:story_id>/chapter/<int:chapter_order>/')
@db_session
def view(story_id, chapter_order=None):
    story = get_story(story_id)
    user = current_user._get_current_object()

    if chapter_order is not None:
        chapter = Chapter.get(story=story_id, order=chapter_order)
        if not chapter:
            abort(404)
        page_title = chapter.title[:80] + ' : ' + story.title
        prev_chapter = chapter.get_prev_chapter()
        next_chapter = chapter.get_next_chapter()
        if user.is_authenticated:
            chapter.bl.viewed(user)
        data = {
            'story': story,
            'chapter': chapter,
            'prev_chapter': prev_chapter,
            'next_chapter': next_chapter,
            'page_title': page_title,
            'allchapters': False
        }
    else:
        chapters = story.chapters.select().order_by(Chapter.order, Chapter.id)[:]
        page_title = story.title + ' – все главы'
        if user.is_authenticated:
            for c in chapters:
                c.bl.viewed(user)
        data = {
            'story': story,
            'chapters': chapters,
            'page_title': page_title,
            'allchapters': True
        }

    return render_template('chapter_view.html', **data)


@bp.route('/story/<int:story_id>/chapter/add/', methods=('GET', 'POST'))
@db_session
def add(story_id):
    story = Story.get(id=story_id)
    if not story:
        abort(404)
    user = current_user._get_current_object()
    if not story.editable_by(user):
        abort(403)

    form = ChapterForm(data={'button_submit': 'Добавить'})
    if form.validate_on_submit():
        chapter = Chapter.bl.create(
            story=story,
            title=form.title.data,
            notes=form.notes.data,
            text=form.text.data,
        )
        return redirect(url_for('chapter.edit', pk=chapter.id))

    data = {
        'page_title': 'Добавление новой главы',
        'story': story,
        'form': form
    }

    return render_template('chapter_work.html', **data)


@bp.route('/chapter/<int:pk>/edit/', methods=('GET', 'POST'))
@db_session
def edit(pk):
    chapter = Chapter.get(id=pk)
    if not chapter:
        abort(404)
    user = current_user._get_current_object()
    if not chapter.story.editable_by(user):
        abort(403)

    chapter_data = {
        'title': chapter.title,
        'notes': chapter.notes,
        'text': chapter.text,
        'button_submit': 'Сохранить изменения',
    }

    form = ChapterForm(data=chapter_data)
    if form.validate_on_submit():
        chapter.bl.update(
            title=form.title.data,
            notes=form.notes.data,
            text=form.text.data,
        )
        return redirect(url_for('chapter.edit', pk=chapter.id))

    data = {
        'page_title': 'Редактирование главы «%s»' % chapter.title,
        'chapter': chapter,
        'form': form
    }

    return render_template('chapter_work.html', **data)


@bp.route('/chapter/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
def delete(pk):
    chapter = Chapter.get(id=pk)
    if not chapter:
        abort(404)
    user = current_user._get_current_object()
    if not chapter.story.editable_by(user):
        abort(403)

    story = chapter.story

    if request.method == 'POST':
        chapter.bl.delete()
        return redirect(url_for('story.edit', pk=story.id))

    data = {
        'page_title': 'Подтверждение удаления главы',
        'story': story,
        'chapter': chapter,
    }

    return render_template('chapter_confirm_delete.html', **data)
