#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, jsonify, redirect, url_for, request, render_template
from flask_login import login_required
from flask_login import current_user
from flask_babel import gettext as _
from pony.orm import db_session


bp = Blueprint('notifications', __name__)


@bp.route('/')
@db_session
def index():
    is_popup = request.args.get('popup') == '1'

    if not current_user.is_authenticated:
        if is_popup:
            return jsonify(popup='?', success=True)
        return redirect(url_for('index.index'))

    last_viewed_id = current_user.last_viewed_notification_id
    if request.args.get('last_viewed_id') and request.args['last_viewed_id'].isdigit():
        last_viewed_id = int(request.args.get('last_viewed_id'))

    older = request.args.get('older')
    older = int(older) if older and older.isdigit() else None
    count = 100

    notifications = current_user.bl.get_notifications(older=older, count=count + 1)
    show_older_link = len(notifications) > count
    notifications = notifications[:count]

    pos = -1
    for i, x in enumerate(notifications):
        if x.get('id') <= last_viewed_id:
            pos = i
            break
    if pos > 0 or (pos == 0 and older is not None and notifications[pos].get('id') == last_viewed_id):
        notifications[pos]['show_viewed_line'] = True

    ctx = {
        'notifications': notifications,
        'is_popup': is_popup,
        'older': older,
        'show_older_link': show_older_link,
        'last_viewed_id': last_viewed_id,
        'page_title': _('Notifications'),
    }

    if is_popup:
        result = render_template('notifications_popup.html', **ctx)
        return jsonify(popup=result, last_id=notifications[0]['id'] if notifications else 0, success=True)
    if notifications:
        current_user.bl.set_last_viewed_notification_id(notifications[0]['id'])
    return render_template('notifications.html', **ctx)


@bp.route('/unread_count/', methods=['GET'])
@db_session
def unread_count():
    if not current_user.is_authenticated:
        return jsonify(success=True, unread_count=0, please_login=True)
    return jsonify(success=True, unread_count=current_user.bl.get_unread_notifications_count())



@bp.route('/<int:nid>/set_viewed/', methods=['POST'])
@db_session
@login_required
def set_viewed(nid):
    if nid > 0:
        current_user.bl.set_last_viewed_notification_id(nid)
    return jsonify(success=True, unread_count=current_user.bl.get_unread_notifications_count())
