#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, url_for
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.forms.comment import CommentForm
from mini_fiction.models import Story, StoryLocalComment
from mini_fiction.utils.misc import calc_maxdepth
from mini_fiction.views import common_comment

bp = Blueprint('story_local_comment', __name__)


def get_local_thread(story_id, user):
    story = Story.get(id=story_id)
    if not story:
        abort(404)
    # Проверяем доступ перед созданием StoryLocalThread, чтобы не создавать
    # его зазря, если доступа вдруг не окажется
    if not user.is_staff and not story.bl.is_contributor(user):
        abort(403)
    return story.bl.get_or_create_local_thread()


@bp.route('/story/<int:story_id>/localcomments/', defaults={'comments_page': -1})
@bp.route('/story/<int:story_id>/localcomments/page/<int:comments_page>/')
@db_session
def view(story_id, comments_page):
    user = current_user._get_current_object()
    local = get_local_thread(story_id, user)
    story = local.story

    per_page = user.comments_per_page or current_app.config['COMMENTS_COUNT']['page']
    maxdepth = None if request.args.get('fulltree') == '1' else calc_maxdepth(user)

    last_viewed_comment = story.bl.last_viewed_local_comment_by(user)
    comments_count, paged, comments_tree_list = local.bl.paginate_comments(comments_page, per_page, maxdepth, last_viewed_comment=last_viewed_comment)
    if not comments_tree_list and paged.number != 1:
        abort(404)

    if comments_page < 0 or comments_page == paged.num_pages:
        story.bl.viewed_localcomments(user)

    data = {
        'story': story,
        'local': local,
        'comments_tree_list': comments_tree_list,
        'comments_count': comments_count,
        'last_viewed_comment': last_viewed_comment,
        'page_title': 'Обсуждение «{}»'.format(story.title),
        'comment_form': CommentForm(),
        'page_obj': paged,
        'sub_comments': story.bl.get_local_comments_subscription(user),
    }
    return render_template('story_localcomments.html', **data)


@bp.route('/story/<int:story_id>/localcomments/add/', methods=('GET', 'POST'))
@db_session
def add(story_id):
    local = get_local_thread(story_id, current_user._get_current_object())

    # Все проверки доступа там
    return common_comment.add(
        'local',
        local,
        template='story_local_comment_work.html',
    )


@bp.route('/story/<int:story_id>/localcomments/<int:local_id>/')
@db_session
def show(story_id, local_id):
    local = get_local_thread(story_id, current_user._get_current_object())
    comment = StoryLocalComment.get(local=local, local_id=local_id)
    if not comment or (comment.deleted and not current_user.is_staff):
        abort(404)

    return common_comment.show('local', comment)


@bp.route('/story/<int:story_id>/localcomments/<int:local_id>/edit/', methods=('GET', 'POST'))
@db_session
def edit(story_id, local_id):
    local = get_local_thread(story_id, current_user._get_current_object())
    comment = StoryLocalComment.get(local=local, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.edit(
        'local',
        comment,
        template='story_local_comment_work.html',
    )


@bp.route('/story/<int:story_id>/localcomments/<int:local_id>/delete/', methods=('GET', 'POST'))
@db_session
def delete(story_id, local_id):
    local = get_local_thread(story_id, current_user._get_current_object())
    comment = StoryLocalComment.get(local=local, local_id=local_id, deleted=False)
    if not comment:
        abort(404)

    return common_comment.delete(
        'local',
        comment,
        template='story_local_comment_delete.html',
        template_ajax='includes/ajax/story_local_comment_delete.html',
        template_ajax_modal=True,
    )


@bp.route('/story/<int:story_id>/localcomments/<int:local_id>/restore/', methods=('GET', 'POST'))
@db_session
def restore(story_id, local_id):
    local = get_local_thread(story_id, current_user._get_current_object())
    comment = StoryLocalComment.get(local=local, local_id=local_id, deleted=True)
    if not comment:
        abort(404)

    return common_comment.restore(
        'local',
        comment,
        template='story_local_comment_restore.html',
        template_ajax='includes/ajax/story_local_comment_restore.html',
        template_ajax_modal=True,
    )


@bp.route('/ajax/story/<int:story_id>/localcomments/page/<int:page>/')
@db_session
def ajax(story_id, page):
    local = get_local_thread(story_id, current_user._get_current_object())

    per_page = current_user.comments_per_page or current_app.config['COMMENTS_COUNT']['page']
    link = url_for('story_local_comment.view', story_id=local.story.id, comments_page=page)

    if request.args.get('last_comment') and request.args['last_comment'].isdigit():
        last_viewed_comment = int(request.args['last_comment'])
    else:
        last_viewed_comment = local.story.bl.last_viewed_local_comment_by(current_user)

    return common_comment.ajax(
        'local',
        local,
        link,
        page,
        per_page,
        template_pagination='includes/comments_pagination_story_local.html',
        last_viewed_comment=last_viewed_comment,
    )


@bp.route('/ajax/story/<int:story_id>/localcomments/tree/<int:local_id>/')
@db_session
def ajax_tree(story_id, local_id):
    local = get_local_thread(story_id, current_user._get_current_object())

    comment = local.comments.select(lambda x: x.local_id == local_id).first()
    if not comment:
        abort(404)

    if request.args.get('last_comment') and request.args['last_comment'].isdigit():
        last_viewed_comment = int(request.args['last_comment'])
    else:
        last_viewed_comment = local.story.bl.last_viewed_local_comment_by(current_user)

    return common_comment.ajax_tree(
        'local',
        comment,
        target=local,
        last_viewed_comment=last_viewed_comment,
    )
