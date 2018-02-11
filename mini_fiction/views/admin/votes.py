#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, request
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

    objects = objects.prefetch(Vote.story, Vote.author)

    page_obj = Paginator(page, objects.count(), per_page=100)

    return render_template(
        'admin/votes/index.html',
        votes=page_obj.slice_or_404(objects),
        page_obj=page_obj,
        page_title='Оценки',
        endpoint=request.endpoint,
        args=args,
    )
