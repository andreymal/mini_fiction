#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from flask import Blueprint, render_template, abort, url_for, redirect, request
from pony.orm import select, db_session, count

from mini_fiction.utils.views import admin_required
from mini_fiction import models
from mini_fiction.utils.misc import Paginator

bp = Blueprint('admin_abuse_reports', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    raw_objects = select((x.target_type, x.target_id, count(x.id), max(x.id)) for x in models.AbuseReport).order_by(-4)

    page_obj = Paginator(page, raw_objects.count(), per_page=100)
    raw_objects = page_obj.slice_or_404(raw_objects)

    abuse_reports_ids = [x[3] for x in raw_objects]
    abuse_reports_dict = {x.id: x for x in models.AbuseReport.select(lambda x: x.id in abuse_reports_ids)}

    abuse_reports = []
    for x in raw_objects:
        item = {
            'abuse': abuse_reports_dict[x[3]],
            'target_type': x[0],
            'target_id': x[1],
            'count': x[2],
            'target': None,
            'deleted': False,
        }

        if item['target_type'] == 'story':
            item['target'] = models.Story.get(id=item['target_id'])
        elif item['target_type'] == 'storycomment':
            item['target'] = models.StoryComment.get(id=item['target_id'])
        elif item['target_type'] == 'newscomment':
            item['target'] = models.NewsComment.get(id=item['target_id'])

        if not item['target']:
            item['deleted'] = True

        abuse_reports.append(item)

    return render_template(
        'admin/abuse_reports/index.html',
        page_title='Жалобы',
        abuse_reports=abuse_reports,
        page_obj=page_obj,
    )


@bp.route('/<int:abuse_id>/', methods=['GET', 'POST'])
@db_session
@admin_required
def show(abuse_id):
    abuse = models.AbuseReport.get(id=abuse_id)
    if not abuse:
        abort(404)

    all_abuses = models.AbuseReport.select(
        lambda x: x.target_type == abuse.target_type and x.target_id == abuse.target_id
    )[:]
    all_abuses.sort(key=lambda x: -x.id)

    saved = False
    if request.method == 'POST':
        if request.form.get('status') == 'none':
            if abuse.resolved_at:
                for x in all_abuses:
                    x.resolved_at = None
                    x.accepted = False
            saved = True

        elif request.form.get('status') == 'accepted':
            if not abuse.resolved_at or not abuse.accepted:
                for x in all_abuses:
                    x.resolved_at = datetime.utcnow()
                    x.accepted = True
            saved = True

        elif request.form.get('status') == 'rejected':
            if not abuse.resolved_at or abuse.accepted:
                for x in all_abuses:
                    x.resolved_at = datetime.utcnow()
                    x.accepted = False
            saved = True

    if all_abuses[0].id != abuse.id:
        return redirect(url_for('admin_abuse_reports.show', abuse_id=all_abuses[0].id))

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
