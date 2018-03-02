#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, Markup, current_app, render_template, abort, request, jsonify, redirect, url_for
from flask_babel import gettext
from flask_login import current_user, login_required
from pony.orm import db_session

from mini_fiction.models import NewsItem
from mini_fiction.forms.comment import CommentForm
from mini_fiction.utils.views import paginate_view
from mini_fiction.utils.misc import calc_maxdepth

bp = Blueprint('news', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
def index(page):
    objects = NewsItem.select().order_by(NewsItem.id.desc())

    return paginate_view(
        'news/index.html',
        objects,
        count=objects.count(),
        page_title=gettext('News'),
        objlistname='news',
        per_page=100,
    )


@bp.route('/<name>/', defaults={'comments_page': -1})
@bp.route('/<name>/comments/page/<int:comments_page>/')
@db_session
def show(name, comments_page):
    newsitem = NewsItem.get(name=name)
    if not newsitem:
        abort(404)

    if newsitem.is_template:
        template = current_app.jinja_env.from_string(newsitem.content)
        template.name = 'db/news/{}.html'.format(name)
        content = render_template(template, newsitem_name=newsitem.name, newsitem_title=newsitem.title)
    else:
        content = newsitem.content

    per_page = current_user.comments_per_page or current_app.config['COMMENTS_COUNT']['page']
    maxdepth = None if request.args.get('fulltree') == '1' else calc_maxdepth(current_user)

    comments_count, paged, comments_tree_list = newsitem.bl.paginate_comments(comments_page, per_page, maxdepth)
    paged.page_arg_name = 'comments_page'
    if not comments_tree_list and paged.number != 1:
        abort(404)

    comment_ids = [x[0].id for x in comments_tree_list]
    if current_user.is_authenticated:
        comment_votes_cache = newsitem.bl.select_comment_votes(current_user._get_current_object(), comment_ids)
    else:
        comment_votes_cache = {i: 0 for i in comment_ids}

    data = {
        'page_title': newsitem.title,
        'newsitem': newsitem,
        'content': Markup(content),
        'comments_count': comments_count,
        'page_obj': paged,
        'comments_tree_list': comments_tree_list,
        'comment_form': CommentForm(),
        'comment_votes_cache': comment_votes_cache,
        'sub_comments': newsitem.bl.get_comments_subscription(current_user._get_current_object()),
    }

    return render_template('news/show.html', **data)


@bp.route('/<name>/comments/subscribe/', methods=('POST',))
@db_session
@login_required
def comments_subscribe(name):
    user = current_user._get_current_object()
    newsitem = NewsItem.get(name=name)
    if not newsitem:
        abort(404)

    newsitem.bl.subscribe_to_comments(
        user,
        email=request.form.get('email') == '1',
        tracker=request.form.get('tracker') == '1',
    )

    if request.form.get('short') == '1':
        return jsonify(success=True)
    return redirect(url_for('newsitem.show', name=newsitem.name))
