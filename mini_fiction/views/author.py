#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for, jsonify
import flask_babel
from flask_babel import gettext
from flask_login import current_user, login_required, logout_user
from pony.orm import db_session, desc

from mini_fiction.bl.migration import enrich_stories
from mini_fiction.models import Author, Story, StoryComment, Contact, ChangeEmailProfile
from mini_fiction.utils.misc import Paginator
from mini_fiction.utils.views import cached_lists
from mini_fiction.forms.author import AuthorEditEmailForm, AuthorEditPasswordForm
from mini_fiction.forms.author import AuthorEditProfileForm, AuthorEditPrefsForm, AuthorEditSubscriptionsForm
from mini_fiction.validation import ValidationError

bp = Blueprint('author', __name__)


def _get_user_for_edit(user_id=None, select_for_update=False):
    if user_id is None and current_user.id is not None:
        user_id = current_user.id
    if user_id is None:
        abort(404)

    try:
        user_id = int(user_id)
    except ValueError:
        abort(404)

    if user_id != current_user.id and not current_user.is_superuser:
        abort(403)

    try:
        if select_for_update:
            user = Author.get_for_update(id=user_id)
        else:
            user = Author.get(id=user_id)
    except ValueError:  # int out of range
        user = None

    if user is None:
        abort(404)
    return user



@bp.route('/profile/', defaults={'user_id': None, 'comments_page': 1})
@bp.route('/profile/comments/page/<int:comments_page>/', defaults={'user_id': None})
@bp.route('/<user_id>/', defaults={'comments_page': 1})
@bp.route('/<user_id>/comments/page/<int:comments_page>/')
@db_session
def info(user_id=None, comments_page=1):
    if user_id is not None:
        try:
            user_id = int(user_id)
        except ValueError:
            abort(404)

    data = {}

    if user_id is None:
        if not current_user.is_authenticated:
            abort(403)
        author = current_user
        comments_list = StoryComment.bl.select_by_story_author(author)
        comments_list = comments_list.sort_by(desc(StoryComment.id))
        stories = list(author.stories)
        stories.sort(key=lambda x: x.first_published_at or x.date, reverse=True)
        contributing_stories = list(author.contributing_stories)
        contributing_stories.sort(key=lambda x: x.first_published_at or x.date, reverse=True)

        data['all_views'] = Story.bl.get_all_views_for_author(author)

        data['page_title'] = gettext('My cabinet')
        template = 'author_dashboard.html'
    else:
        author = Author.get(id=user_id)
        if not author:
            abort(404)
        author_id = author.id  # обход утечки памяти
        comments_list = StoryComment.select(lambda x: x.author.id == author_id and not x.deleted and x.story_published)
        comments_list = comments_list.sort_by(desc(StoryComment.id))
        data['page_title'] = gettext('Author: {author}').format(author=author.username)
        stories = list(Story.bl.select_by_author(author, for_user=current_user))
        stories.sort(key=lambda x: x.first_published_at or x.date, reverse=True)
        contributing_stories = None
        template = 'author_overview.html'

    comments_count = comments_list.count()
    series = list(author.series)
    paged = Paginator(
        number=comments_page,
        total=comments_count,
        per_page=current_app.config['COMMENTS_COUNT']['author_page'],
        page_arg_name='comments_page',
    )  # TODO: restore orphans?
    comments = paged.slice(comments_list)
    if not comments and comments_page != 1:
        abort(404)

    enrich_stories(stories)

    data.update({
        'author': author,
        'is_system_user': author.id == current_app.config['SYSTEM_USER_ID'],
        'sub': author.bl.get_stories_subscription(current_user),
        'stories': stories,
        'contributing_stories': contributing_stories,
        'series': series,
        'comments': comments,
        'comments_count': comments_count,
        'comments_short': True,
        'page_obj': paged,
    })

    story_ids = set(x.id for x in stories)
    if contributing_stories:
        story_ids |= set(x.id for x in contributing_stories)
    story_ids |= set(x.story.id for x in comments)

    data.update(cached_lists(story_ids))

    return render_template(template, **data)


@bp.route('/profile/edit/', defaults={'user_id': None}, methods=('GET', 'POST'))
@bp.route('/<user_id>/edit/', methods=('GET', 'POST'))
@db_session
@login_required
def edit_general(user_id=None):
    user = _get_user_for_edit(user_id, select_for_update=request.method == 'POST')

    contacts = list(Contact.select(lambda x: x.author == user).order_by(Contact.id))

    form = AuthorEditProfileForm(data={
        'bio': user.bio,
        'contacts': [
            {'name': c.name, 'value': c.value}
            for c in contacts
        ] + [{'name': '', 'value': ''}]
    })

    if user.image is None:
        del form.delete_avatar

    ctx = {
        'page_title': 'Основные настройки',
        'settings_tab': 'general',
        'user': user,
        'user_is_current': user.id == current_user.id,
        'form': form,
        'non_field_errors': [],
        'saved': False,
    }

    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                user.bl.update(
                    form.data,
                    modified_by_user=current_user,
                    fill_admin_log=user.id != current_user.id,
                )
            except ValidationError as exc:
                form.set_errors(exc.errors)
            else:
                ctx['saved'] = True

    return render_template('profile_edit_general.html', **ctx)


@bp.route('/profile/edit/mail/', defaults={'user_id': None}, methods=('GET', 'POST'))
@bp.route('/<user_id>/edit/mail/', methods=('GET', 'POST'))
@db_session
@login_required
def edit_mail(user_id=None):
    user = _get_user_for_edit(user_id, select_for_update=request.method == 'POST')

    cep = ChangeEmailProfile.get(user=user)
    new_email = cep.email if cep else None

    form = AuthorEditEmailForm(data={'email': new_email or user.email})
    non_field_errors = []

    ctx = {
        'page_title': 'Настройки почты',
        'settings_tab': 'mail',
        'user': user,
        'user_is_current': user.id == current_user.id,
        'form': form,
        'non_field_errors': non_field_errors,
        'new_email': new_email,
        'email_changed': False,
        'saved': False,
    }

    if request.method == 'POST':
        if form.validate_on_submit():
            if not user.bl.check_password(form.password.data):
                non_field_errors.append(gettext('Password is incorrect'))
            else:
                try:
                    ctx['email_changed'] = user.bl.update_email_with_confirmation(form.email.data)
                    ctx['new_email'] = form.email.data if ctx['email_changed'] else None
                    ctx['saved'] = True
                except ValidationError as exc:
                    form.set_errors(exc.errors)

    return render_template('profile_edit_mail.html', **ctx)


@bp.route('/profile/edit/security/', defaults={'user_id': None}, methods=('GET', 'POST'))
@bp.route('/<user_id>/edit/security/', methods=('GET', 'POST'))
@db_session
@login_required
def edit_security(user_id=None):
    user = _get_user_for_edit(user_id, select_for_update=request.method == 'POST')

    password_form = AuthorEditPasswordForm()
    password_form_errors = []

    ctx = {
        'page_title': 'Настройки безопасности',
        'settings_tab': 'security',
        'user': user,
        'user_is_current': user.id == current_user.id,
        'password_form': password_form,
        'password_form_errors': password_form_errors,
    }

    if request.method == 'POST':
        if password_form.validate_on_submit():
            if not user.bl.check_password(password_form.old_password.data):
                password_form_errors.append(gettext('Old password is incorrect'))
            elif not user.bl.is_password_good(password_form.new_password_1.data):
                password_form_errors.append(gettext('Password is too bad, please change it'))
            else:
                user.bl.set_password(password_form.new_password_1.data)
                logout_user()
                user.bl.reset_session_token()
                return redirect(url_for('auth.login'))

    return render_template('profile_edit_security.html', **ctx)


@bp.route('/profile/edit/personal/', defaults={'user_id': None}, methods=('GET', 'POST'))
@bp.route('/<user_id>/edit/personal/', methods=('GET', 'POST'))
@db_session
@login_required
def edit_personal(user_id=None):
    user = _get_user_for_edit(user_id, select_for_update=request.method == 'POST')


    form = AuthorEditPrefsForm(data={
        # 'excluded_categories': user.excluded_categories_list,
        'timezone': user.timezone or current_app.config['BABEL_DEFAULT_TIMEZONE'],
        'detail_view': user.detail_view,
        'nsfw': user.nsfw,
        'comments_per_page': (
            user.comments_per_page
            if user.comments_per_page is not None
            else current_app.config['COMMENTS_COUNT']['page']
        ),
        'comments_maxdepth': (
            user.comments_maxdepth
            if user.comments_maxdepth is not None
            else current_app.config['COMMENTS_TREE_MAXDEPTH']
        ),
        'comment_spoiler_threshold': (
            user.comment_spoiler_threshold
            if user.comment_spoiler_threshold is not None
            else current_app.config['COMMENT_SPOILER_THRESHOLD']
        ),
        'header_mode': {'': 2, 'off': 0, 'l': 1, 'ls': 2}[user.header_mode],
        'text_source_behaviour': user.text_source_behaviour,
    })
    non_field_errors = []

    ctx = {
        'page_title': 'Настройки внешнего вида и отображения',
        'settings_tab': 'personal',
        'user': user,
        'user_is_current': user.id == current_user.id,
        'form': form,
        'non_field_errors': non_field_errors,
        'saved': False,
        'date_now': datetime.utcnow(),
    }

    if request.method == 'POST':
        if form.validate_on_submit():
            prefs_data = dict(form.data)
            if prefs_data.get('header_mode') == 0:
                prefs_data['header_mode'] = 'off'
            elif prefs_data.get('header_mode') == 1:
                prefs_data['header_mode'] = 'l'
            elif prefs_data.get('header_mode') == 2:
                prefs_data['header_mode'] = 'ls'
            else:
                prefs_data.pop('header_mode', None)
            user.bl.update(
                    prefs_data,
                    modified_by_user=current_user,
                    fill_admin_log=user.id != current_user.id,
                )
            if user.id == current_user.id:
                flask_babel.refresh()  # update timezone
            ctx['saved'] = True

    return render_template('profile_edit_personal.html', **ctx)


@bp.route('/profile/edit/subscriptions/', defaults={'user_id': None}, methods=('GET', 'POST'))
@bp.route('/<user_id>/edit/subscriptions/', methods=('GET', 'POST'))
@db_session
@login_required
def edit_subscriptions(user_id=None):
    user = _get_user_for_edit(user_id, select_for_update=request.method == 'POST')

    silent_email = user.silent_email_list
    silent_tracker = user.silent_tracker_list
    form = AuthorEditSubscriptionsForm(data={
        'email_abuse_report': 'abuse_report' not in silent_email,
        'email_story_pubrequest': 'story_pubrequest' not in silent_email,
        'email_story_publish_noappr': 'story_publish_noappr' not in silent_email,
        'email_story_delete': 'story_delete' not in silent_email,

        'email_story_publish': 'story_publish' not in silent_email,
        'tracker_story_publish': 'story_publish' not in silent_tracker,

        'email_story_draft': 'story_draft' not in silent_email,
        'tracker_story_draft': 'story_draft' not in silent_tracker,

        'email_story_reply': 'story_reply' not in silent_email,
        'tracker_story_reply': 'story_reply' not in silent_tracker,

        'email_story_lreply': 'story_lreply' not in silent_email,
        'tracker_story_lreply': 'story_lreply' not in silent_tracker,

        'email_news_reply': 'news_reply' not in silent_email,
        'tracker_news_reply': 'news_reply' not in silent_tracker,
    })
    non_field_errors = []

    ctx = {
        'page_title': 'Настройки уведомлений и подписок',
        'settings_tab': 'subscriptions',
        'user': user,
        'user_is_current': user.id == current_user.id,
        'form': form,
        'non_field_errors': non_field_errors,
        'saved': False,
    }

    if request.method == 'POST':
        if form.validate_on_submit():
            user.bl.update_email_subscriptions({
                'abuse_report': form.email_abuse_report.data,
                'story_pubrequest': form.email_story_pubrequest.data,
                'story_publish': form.email_story_publish.data,
                'story_publish_noappr': form.email_story_publish_noappr.data,
                'story_draft': form.email_story_draft.data,
                'story_delete': form.email_story_delete.data,
                'story_reply': form.email_story_reply.data,
                'story_lreply': form.email_story_lreply.data,
                'news_reply': form.email_news_reply.data,
            }, modified_by_user=current_user, fill_admin_log=user.id != current_user.id)
            user.bl.update_tracker_subscriptions({
                'story_publish': form.tracker_story_publish.data,
                'story_draft': form.tracker_story_draft.data,
                'story_reply': form.tracker_story_reply.data,
                'story_lreply': form.tracker_story_lreply.data,
                'news_reply': form.tracker_news_reply.data,
            }, modified_by_user=current_user, fill_admin_log=user.id != current_user.id)
            ctx['saved'] = True

    return render_template('profile_edit_subscriptions.html', **ctx)


@bp.route('/<user_id>/ban/', methods=('POST',))
@db_session
def ban(user_id):
    try:
        user_id = int(user_id)
    except Exception:
        abort(404)

    if current_user.is_staff and user_id not in (current_app.config['SYSTEM_USER_ID'], current_user.id):
        author = Author.get(id=user_id)
        if not author:
            abort(404)
        author.bl.update(
            {'is_active': not author.is_active},
            modified_by_user=current_user,
            fill_admin_log=True,
        )
        return redirect(url_for('author.info', user_id=user_id))
    else:
        abort(403)


@bp.route('/<user_id>/subscribe/', methods=('POST',))
@db_session
@login_required
def subscribe(user_id):
    try:
        user_id = int(user_id)
    except Exception:
        abort(404)

    author = Author.get(id=user_id)
    if not author:
        abort(404)

    author.bl.subscribe_to_new_stories(
        current_user,
        email=request.form.get('email') == '1',
        tracker=request.form.get('tracker') == '1',
    )

    if request.form.get('short') == '1':
        return jsonify(success=True)
    return redirect(url_for('author.info', user_id=author.id))
