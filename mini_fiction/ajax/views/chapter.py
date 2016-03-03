#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import db_session
from flask import Blueprint, request, abort, render_template
from flask_login import current_user

from mini_fiction.ajax.utils import ajax_login_required
from mini_fiction.models import Story, Chapter


bp = Blueprint('ajax_chapter', __name__)


@bp.route('/story/<int:story_id>/sort/', methods=('POST',))
@db_session
@ajax_login_required
def sort(story_id):
    story = Story.get(id=story_id)
    if not story:
        abort(404)
    if not story.editable_by(current_user._get_current_object()):
        abort(403)

    new_order = [int(c) for c in request.form.getlist('chapter[]')]
    chapters = {c.id: c for c in story.chapters}
    if not new_order or set(chapters) != set(new_order):
        return 'Bad request. Incorrect list!', 400
    else:
        for new_order_id, chapter_id in enumerate(new_order):
            chapters[chapter_id].order = new_order_id + 1
        return 'Done'


@bp.route('/chapter/<int:pk>/delete/', methods=('GET', 'POST',))
@db_session
@ajax_login_required
def delete(pk):
    chapter = Chapter.get(id=pk)
    if not chapter:
        abort(404)
    story = chapter.story
    if not story.editable_by(current_user._get_current_object()):
        abort(403)

    if request.method == 'POST':
        chapter.bl.delete()
        return str(pk)

    return render_template('includes/ajax/chapter_ajax_confirm_delete.html', page_title='Подтверждение удаления рассказа', story=story, chapter=chapter)
