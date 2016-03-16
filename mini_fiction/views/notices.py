#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, Markup, current_app, render_template, abort, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.models import Notice
from mini_fiction.forms.comment import CommentForm
from mini_fiction.utils.views import paginate_view

bp = Blueprint('notices', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
def index(page):
    objects = Notice.select().order_by(Notice.id.desc())

    return paginate_view(
        'notices/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('Notices'),
        objlistname='notices',
        per_page=100,
    )


@bp.route('/<name>/', defaults={'comments_page': -1})
@bp.route('/<name>/comments/page/<int:comments_page>/')
@db_session
def show(name, comments_page):
    notice = Notice.get(name=name)
    if not notice:
        abort(404)

    if notice.is_template:
        template = current_app.jinja_env.from_string(notice.content)
        template.name = 'db/notices/{}.html'.format(name)
        content = render_template(template, notice_name=notice.name, notice_title=notice.title)
    else:
        content = notice.content

    per_page = current_app.config['COMMENTS_COUNT']['page']
    comment_spoiler_threshold = current_app.config['COMMENT_SPOILER_THRESHOLD']
    maxdepth = None if request.args.get('fulltree') == '1' else 2

    comments_count, paged, comments_tree_list = notice.bl.paginate_comments(comments_page, per_page, maxdepth)
    if not comments_tree_list and paged.number != 1:
        abort(404)

    comment_ids = [x[0].id for x in comments_tree_list]
    if current_user.is_authenticated:
        comment_votes_cache = notice.bl.select_comment_votes(current_user._get_current_object(), comment_ids)
    else:
        comment_votes_cache = {i: 0 for i in comment_ids}

    data = {
        'page_title': notice.title,
        'notice': notice,
        'content': Markup(content),
        'comments_count': comments_count,
        'page_obj': paged,
        'comment_spoiler_threshold': comment_spoiler_threshold,
        'comments_tree_list': comments_tree_list,
        'comment_form': CommentForm(),
        'comment_votes_cache': comment_votes_cache,
    }

    return render_template('notices/show.html', **data)
