#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from flask import Blueprint, current_app, render_template, abort, request, redirect, url_for
from flask_login import current_user
from pony.orm import db_session, select

from mini_fiction.models import Author, Vote
from mini_fiction.utils.misc import Paginator

bp = Blueprint('admin_votes', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
def index(page):
    if not current_user.is_staff:
        abort(403)

    objects = Vote.select().order_by(Vote.id.desc())

    args = {
        'page': page,
    }

    if request.args.get('story_id'):
        try:
            story_id = int(request.args['story_id'])
        except ValueError:
            pass
        else:
            args['story_id'] = story_id
            objects = objects.filter(lambda x: x.story.id == story_id)

    if request.args.get('username'):
        args['username'] = request.args['username']
        user_ids = select(x.id for x in Author if args['username'].lower() in x.username.lower())[:]
        objects = objects.filter(lambda x: x.author.id in user_ids)

    if request.args.get('ip'):
        args['ip'] = request.args['ip']
        objects = objects.filter(lambda x: x.ip == args['ip'])

    if request.args.get('revoked') == 'no':
        args['revoked'] = 'no'
        objects = objects.filter(lambda x: x.revoked_at is None)
    elif request.args.get('revoked') == 'yes':
        args['revoked'] = 'yes'
        objects = objects.filter(lambda x: x.revoked_at is not None)

    objects = objects.prefetch(Vote.story, Vote.author)

    page_obj = Paginator(page, objects.count(), per_page=100, endpoint=request.endpoint, view_args=args)

    return render_template(
        'admin/votes/index.html',
        votes=page_obj.slice_or_404(objects),
        page_obj=page_obj,
        page_title='Оценки',
        endpoint=request.endpoint,
        args=args,
    )


@bp.route('/manyupdate/', methods=['GET', 'POST'])
@db_session
def manyupdate():
    if request.method != 'POST':
        return redirect(url_for('admin_votes.index'))
    if not current_user.is_superuser:
        abort(403)

    return_path = request.form.get('return_path')
    if not return_path or return_path.startswith('//') or not return_path.startswith('/'):
        return_path = url_for('admin_votes.index')

    vote_ids = [int(x) for x in request.form.getlist('vote') if x and x.isdigit()]
    all_votes = Vote.select(lambda x: x.id in vote_ids)[:]

    act = request.form.get('act')

    update_stories_rating = set()
    for vote in all_votes:
        if act == 'revoke' and not vote.revoked_at:
            vote.revoked_at = datetime.utcnow()
            update_stories_rating.add(vote.story)
        if act == 'restore' and vote.revoked_at:
            vote.revoked_at = None
            update_stories_rating.add(vote.story)
        vote.flush()

    for story in update_stories_rating:
        story.bl.update_rating()

    return redirect(return_path)
