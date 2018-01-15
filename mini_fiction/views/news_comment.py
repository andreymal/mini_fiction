#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, abort, url_for
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.models import NewsItem, NewsComment
from mini_fiction.views import common_comment

bp = Blueprint('news_comment', __name__)


def parse_news_id(news_id):
    if not news_id.isdigit():
        newsitem = NewsItem.get(name=news_id)
        if not newsitem:
            abort(404)
        return newsitem.id
    return int(news_id)


@bp.route('/news/<news_id>/comment/add/', methods=('GET', 'POST'))
@db_session
def add(news_id):
    newsitem = NewsItem.get(id=parse_news_id(news_id))
    if not newsitem:
        abort(404)

    # Все проверки доступа там
    return common_comment.add(
        'newsitem',
        newsitem,
        template='news/comment_work.html',
    )


@bp.route('/news/<news_id>/comment/<int:local_id>/')
@db_session
def show(news_id, local_id):
    comment = NewsComment.get(newsitem=parse_news_id(news_id), local_id=local_id)
    if not comment or (comment.deleted and not current_user.is_staff):
        abort(404)

    return common_comment.show('newsitem', comment)


@bp.route('/news/<news_id>/comment/<int:local_id>/edit/', methods=('GET', 'POST'))
@db_session
def edit(news_id, local_id):
    comment = NewsComment.get(newsitem=parse_news_id(news_id), local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.edit(
        'newsitem',
        comment,
        template='news/comment_work.html',
    )


@bp.route('/news/<news_id>/comment/<int:local_id>/delete/', methods=('GET', 'POST'))
@db_session
def delete(news_id, local_id):
    comment = NewsComment.get(newsitem=parse_news_id(news_id), local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.delete(
        'newsitem',
        comment,
        template='news/comment_delete.html',
        template_ajax='news/comment_delete_ajax.html',
        template_ajax_modal=True,
    )


@bp.route('/news/<news_id>/comment/<int:local_id>/restore/', methods=('GET', 'POST'))
@db_session
def restore(news_id, local_id):
    comment = NewsComment.get(newsitem=parse_news_id(news_id), local_id=local_id, deleted=True)
    if not comment:
        abort(404)

    return common_comment.restore(
        'newsitem',
        comment,
        template='news/comment_restore.html',
        template_ajax='news/comment_restore_ajax.html',
        template_ajax_modal=True,
    )


@bp.route('/news/<news_id>/comment/<int:local_id>/vote/', methods=('POST',))
@db_session
def vote(news_id, local_id):
    comment = NewsComment.get(newsitem=parse_news_id(news_id), local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.vote('newsitem', comment)


@bp.route('/ajax/news/<news_id>/comments/page/<int:page>/')
@db_session
def ajax(news_id, page):
    newsitem = NewsItem.get(id=parse_news_id(news_id))
    if not newsitem:
        abort(404)

    per_page = current_user.comments_per_page or current_app.config['COMMENTS_COUNT']['page']
    link = url_for('news.show', name=newsitem.name, comments_page=page)

    return common_comment.ajax(
        'newsitem',
        newsitem,
        link,
        page,
        per_page,
        template_pagination='news/comments_pagination.html',
    )


@bp.route('/ajax/news/<news_id>/comments/tree/<int:local_id>/')
@db_session
def ajax_tree(news_id, local_id):
    newsitem = NewsItem.get(id=parse_news_id(news_id))
    if not newsitem:
        abort(404)

    comment = newsitem.comments.select(lambda x: x.local_id == local_id).first()
    if not comment:
        abort(404)

    return common_comment.ajax_tree(
        'newsitem',
        comment,
        target=newsitem,
    )
