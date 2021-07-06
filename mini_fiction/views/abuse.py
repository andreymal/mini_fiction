#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, g, jsonify, url_for, redirect
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.models import AbuseReport, StoryComment, NewsComment
from mini_fiction.utils.misc import call_after_request as later
from .story import get_story
from .news_comment import parse_news_id

bp = Blueprint('abuse', __name__)


def abuse_common(target_type, target):
    # FIXME: это всё не в bl, нехорошо (но при переносе надо не забыть про проверки доступа)

    if not target or not current_user.is_authenticated:
        abort(404)

    data = {
        'page_title': 'Отправка жалобы',
        'target_type': target_type,
        'target': target,
        'next': request.referrer or url_for('index.index'),
        'abuse': None,
        'can_abuse': True,
        'reason': '',
        'errors': [],
    }

    # Если пользователь уже отправлял жалобу, то он не может отправить её ещё раз
    abuse = list(AbuseReport.select(
        lambda x: x.target_type == target_type and x.target_id == target.id and x.user.id == current_user.id and not x.ignored
    ))
    abuse.sort(key=lambda x: -x.id)
    abuse = abuse[0] if abuse else None
    if abuse:
        data['abuse'] = abuse
        data['can_abuse'] = False

    if not abuse and request.method == 'POST':
        reason = request.form.get('reason') or ''
        data['reason'] = reason

        if not reason.strip():
            data['errors'].append('Причина жалобы не может отсутствовать')

        elif len(reason) > 8192:
            data['errors'].append('Слишком длинно; опишите причину покороче')

        else:
            abuse = AbuseReport(
                target_type=target_type,
                target_id=target.id,
                user=current_user,
                reason=request.form['reason'],
            )
            abuse.flush()

            # Если это первая жалоба на объект, то уведомляем админов
            if AbuseReport.select(
                lambda x: x.target_type == target_type and x.target_id == target.id and not x.ignored and x.resolved_at is None
            ).count() == 1:
                later(current_app.tasks['notify_abuse_report'].delay, abuse.id)

            return redirect(request.form.get('next') or url_for('index.index'), 302)

    if g.is_ajax:
        return jsonify({'page_content': {'modal': render_template('abuse_report_ajax.html', **data)}})
    return render_template('abuse_report.html', **data)


@bp.route('/story/<int:story_id>/', methods=['GET', 'POST'])
@db_session
def abuse_story(story_id):
    return abuse_common('story', get_story(story_id))


@bp.route('/story/<int:story_id>/comment/<int:local_id>/', methods=['GET', 'POST'])
@db_session
def abuse_storycomment(story_id, local_id):
    story = get_story(story_id)  # Здесь проверка доступа
    return abuse_common('storycomment', StoryComment.get(story=story.id, local_id=local_id, deleted=False))


@bp.route('/news/<news_id>/comment/<int:local_id>/', methods=['GET', 'POST'])
@db_session
def abuse_newscomment(news_id, local_id):
    return abuse_common('newscomment', NewsComment.get(newsitem=parse_news_id(news_id), local_id=local_id, deleted=False))
