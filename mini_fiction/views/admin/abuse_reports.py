#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_login import current_user
from pony.orm import select, db_session

from mini_fiction.utils.views import admin_required
from mini_fiction import models
from mini_fiction.utils.misc import Paginator
from mini_fiction.validation.utils import bool_coerce

bp = Blueprint('admin_abuse_reports', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = models.AbuseReport.select().order_by(models.AbuseReport.id.desc())

    args = {
        'page': page,
    }

    target_type = request.args.get('target_type')
    if target_type:
        args['target_type'] = target_type
        objects = objects.filter(lambda x: x.target_type == target_type)
        if request.args.get('target_id'):
            try:
                target_id = int(request.args['target_id'])
            except ValueError:
                pass
            else:
                args['target_id'] = target_id
                objects = objects.filter(lambda x: x.target_id == target_id)

    if request.args.get('username'):
        args['username'] = request.args['username']
        user_ids = select(x.id for x in models.Author if args['username'].lower() in x.username.lower())[:]
        objects = objects.filter(lambda x: x.user.id in user_ids)

    if request.args.get('status') == 'none':
        args['status'] = 'none'
        objects = objects.filter(lambda x: not x.ignored and x.resolved_at is None)
    elif request.args.get('status') == 'accepted':
        args['status'] = 'accepted'
        objects = objects.filter(lambda x: not x.ignored and x.resolved_at is not None and x.accepted)
    elif request.args.get('status') == 'rejected':
        args['status'] = 'rejected'
        objects = objects.filter(lambda x: not x.ignored and x.resolved_at is not None and not x.accepted)
    elif request.args.get('status') == 'ignored':
        args['status'] = 'ignored'
        objects = objects.filter(lambda x: x.ignored)

    objects = objects.prefetch(models.AbuseReport.user)

    page_obj = Paginator(page, objects.count(), per_page=100, endpoint=request.endpoint, view_args=args)
    abuse_reports = page_obj.slice_or_404(objects)

    # Предзагружаем таргеты (prefetch для них не вызвать, к сожалению)
    stories = {}
    story_ids = [x.target_id for x in abuse_reports if x.target_type == 'story']
    if story_ids:
        stories = {x.id: x for x in models.Story.select(lambda s: s.id in story_ids)}

    storycomments = {}
    storycomment_ids = [x.target_id for x in abuse_reports if x.target_type == 'storycomment']
    if storycomment_ids:
        storycomments = {x.id: x for x in models.StoryComment.select(lambda s: s.id in storycomment_ids).prefetch(models.StoryComment.story, models.StoryComment.author)}

    newscomments = {}
    newscomment_ids = [x.target_id for x in abuse_reports if x.target_type == 'newscomment']
    if storycomment_ids:
        newscomments = {x.id: x for x in models.NewsComment.select(lambda s: s.id in newscomment_ids).prefetch(models.NewsComment.newsitem, models.NewsComment.author)}

    return render_template(
        'admin/abuse_reports/index.html',
        page_title='Жалобы',
        abuse_reports=abuse_reports,
        stories=stories,
        storycomments=storycomments,
        newscomments=newscomments,
        page_obj=page_obj,
        endpoint=request.endpoint,
        args=args,
    )


@bp.route('/manyupdate/', methods=['GET', 'POST'])
@db_session
@admin_required
def manyupdate():
    if request.method != 'POST':
        return redirect(url_for('admin_abuse_reports.index'))

    return_path = request.form.get('return_path')
    if not return_path or return_path.startswith('//') or not return_path.startswith('/'):
        return_path = url_for('admin_abuse_reports.index')

    abuse_ids = [int(x) for x in request.form.getlist('abuse') if x and x.isdigit()]
    all_abuses = models.AbuseReport.select(lambda x: x.id in abuse_ids)[:]

    _update_abuses(all_abuses, user=current_user._get_current_object(), status=request.form.get('status'))

    return redirect(return_path)


@bp.route('/<int:abuse_id>/', methods=['GET', 'POST'])
@db_session
@admin_required
def show(abuse_id):
    abuse = models.AbuseReport.get(id=abuse_id)
    if not abuse:
        abort(404)

    if not abuse.ignored:
        all_abuses = models.AbuseReport.select(
            lambda x: x.target_type == abuse.target_type and x.target_id == abuse.target_id and not x.ignored
        )[:]
        all_abuses.sort(key=lambda x: -x.id)
        assert abuse in all_abuses
        all_abuses.remove(abuse)
        all_abuses = [abuse] + all_abuses
    else:
        all_abuses = [abuse]

    saved = False
    if request.method == 'POST':
        edited_abuses = [abuse]
        if bool_coerce(request.form.get('all') or ''):
            edited_abuses += [x for x in all_abuses if x is not abuse and not x.ignored and not x.resolved_at]

        saved = bool(_update_abuses(
            edited_abuses,
            user=current_user._get_current_object(),
            status=request.form.get('status'),
        ))
        if saved and abuse.ignored:
            all_abuses = [abuse]

    target = None
    if abuse.target_type == 'story':
        target = models.Story.get(id=abuse.target_id)
    elif abuse.target_type == 'storycomment':
        target = models.StoryComment.get(id=abuse.target_id)
    elif abuse.target_type == 'newscomment':
        target = models.NewsComment.get(id=abuse.target_id)

    return render_template(
        'admin/abuse_reports/show.html',
        page_title='Жалоба',
        abuse=abuse,
        all_abuses=all_abuses,
        target=target,
        saved=saved,
    )


def _update_abuses(abuses, user, status):
    changed_abuses = []

    for abuse in abuses:
        changed_fields = set()

        if status in ('none', 'accepted', 'rejected'):
            if abuse.ignored:
                abuse.ignored = False
                changed_fields |= {'ignored',}

        if status == 'none':
            if abuse.resolved_at:
                abuse.resolved_at = None
                abuse.accepted = False
                changed_fields |= {'accepted',}

        elif status == 'accepted':
            if not abuse.resolved_at or not abuse.accepted:
                abuse.resolved_at = datetime.utcnow()
                abuse.accepted = True
                changed_fields |= {'accepted',}

        elif status == 'rejected':
            if not abuse.resolved_at or abuse.accepted:
                abuse.resolved_at = datetime.utcnow()
                abuse.accepted = False
                changed_fields |= {'accepted',}

        elif status == 'ignored':
            if not abuse.ignored:
                abuse.resolved_at = None
                abuse.accepted = False
                abuse.ignored = True
            changed_fields |= {'ignored', 'accepted'}

        if changed_fields:
            models.AdminLog.bl.create(
                user=user,
                obj=abuse,
                action=models.AdminLog.CHANGE,
                fields=sorted(changed_fields),
            )
            changed_abuses.append(abuse)

    return changed_abuses
