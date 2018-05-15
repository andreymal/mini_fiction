#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for, jsonify
from flask_babel import gettext
from flask_login import current_user, login_required, logout_user
from pony.orm import db_session

from mini_fiction.models import Author, Story, StoryComment, Contact, ChangeEmailProfile
from mini_fiction.utils.misc import Paginator
from mini_fiction.utils.views import cached_lists
from mini_fiction.forms.author import AuthorEditEmailForm, AuthorEditPasswordForm
from mini_fiction.forms.author import AuthorEditProfileForm, AuthorEditPrefsForm, AuthorEditSubscriptionsForm
from mini_fiction.validation import ValidationError

bp = Blueprint('author', __name__)


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
        author = current_user._get_current_object()
        comments_list = StoryComment.bl.select_by_story_author(author)
        comments_list = comments_list.order_by(StoryComment.id.desc())
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
        comments_list = comments_list.order_by(StoryComment.id.desc())
        data['page_title'] = gettext('Author: {author}').format(author=author.username)
        stories = list(Story.bl.select_by_author(author, for_user=current_user))
        stories.sort(key=lambda x: x.first_published_at or x.date, reverse=True)
        contributing_stories = None
        template = 'author_overview.html'

    comments_count = comments_list.count()
    series = author.series[:]
    paged = Paginator(
        number=comments_page,
        total=comments_count,
        per_page=current_app.config['COMMENTS_COUNT']['author_page'],
        page_arg_name='comments_page',
    )  # TODO: restore orphans?
    comments = paged.slice(comments_list)
    if not comments and comments_page != 1:
        abort(404)

    data.update({
        'author': author,
        'is_system_user': author.id == current_app.config['SYSTEM_USER_ID'],
        'sub': author.bl.get_stories_subscription(current_user._get_current_object()),
        'stories': stories,
        'contributing_stories': contributing_stories,
        'series': series,
        'comments': comments,
        'comments_count': comments_count,
        'comments_short': True,
        'page_obj': paged,
    })
    data.update(cached_lists([x.id for x in stories]))

    return render_template(template, **data)


@bp.route('/profile/edit/', methods=('GET', 'POST'))
@db_session
@login_required
def edit():
    author = current_user._get_current_object()

    cep = ChangeEmailProfile.get(user=author)
    new_email = cep.email if cep else None

    data = {'page_title': gettext('Profile settings'), 'user': author}

    has_avatar = bool(author.avatar_small or author.avatar_medium or author.avatar_large)
    avatar_uploading = bool(current_app.config['AVATARS_UPLOADING'])

    profile_form = None
    email_form = None
    password_form = None
    prefs_form = None
    subs_form = None

    password_form_errors = []
    email_form_errors = []

    if request.method == 'POST' and request.form:
        if 'save_password' in request.form:
            password_form = AuthorEditPasswordForm()
            if password_form.validate_on_submit():
                if not author.bl.authenticate(password_form.old_password.data):
                    password_form_errors.append(gettext('Old password is incorrect'))
                elif not author.bl.is_password_good(password_form.new_password_1.data):
                    password_form_errors.append(gettext('Password is too bad, please change it'))
                else:
                    author.bl.set_password(password_form.new_password_1.data)
                    logout_user()
                    author.bl.reset_session_token()
                    return redirect(url_for('auth.login'))

        if 'save_profile' in request.form:
            profile_form = AuthorEditProfileForm()
            if not has_avatar:
                del profile_form.delete_avatar
            if not avatar_uploading:
                del profile_form.avatar

            if profile_form.validate_on_submit():
                try:
                    author.bl.update(profile_form.data)
                except ValidationError as exc:
                    profile_form.set_errors(exc.errors)
                else:
                    data['profile_ok'] = True

        if 'save_email' in request.form:
            email_form = AuthorEditEmailForm()
            if email_form.validate_on_submit():
                if not author.bl.authenticate(email_form.password.data):
                    email_form_errors.append(gettext('Password is incorrect'))
                else:
                    try:
                        data['email_changed'] = author.bl.update_email_with_confirmation(email_form.email.data)
                        data['email_ok'] = True
                    except ValidationError as exc:
                        email_form.set_errors(exc.errors)

        if 'save_prefs' in request.form:
            prefs_form = AuthorEditPrefsForm()
            if prefs_form.validate_on_submit():
                prefs_data = dict(prefs_form.data)
                if prefs_data.get('header_mode') == 0:
                    prefs_data['header_mode'] = 'off'
                elif prefs_data.get('header_mode') == 1:
                    prefs_data['header_mode'] = 'l'
                elif prefs_data.get('header_mode') == 2:
                    prefs_data['header_mode'] = 'ls'
                else:
                    prefs_data.pop('header_mode', None)
                author.bl.update(prefs_data)
                data['prefs_ok'] = True

        if 'save_subs' in request.form:
            subs_form = AuthorEditSubscriptionsForm()
            if subs_form.validate_on_submit():
                author.bl.update_email_subscriptions({
                    'abuse_report': subs_form.email_abuse_report.data,
                    'story_pubrequest': subs_form.email_story_pubrequest.data,
                    'story_publish': subs_form.email_story_publish.data,
                    'story_publish_noappr': subs_form.email_story_publish_noappr.data,
                    'story_draft': subs_form.email_story_draft.data,
                    'story_delete': subs_form.email_story_delete.data,
                    'story_reply': subs_form.email_story_reply.data,
                    'story_lreply': subs_form.email_story_lreply.data,
                    'news_reply': subs_form.email_news_reply.data,
                })
                author.bl.update_tracker_subscriptions({
                    'story_publish': subs_form.tracker_story_publish.data,
                    'story_draft': subs_form.tracker_story_draft.data,
                    'story_reply': subs_form.tracker_story_reply.data,
                    'story_lreply': subs_form.tracker_story_lreply.data,
                    'news_reply': subs_form.tracker_news_reply.data,
                })
                data['subs_ok'] = True

    if not profile_form:
        contacts = Contact.select(lambda x: x.author == author).order_by(Contact.id)[:]
        profile_form = AuthorEditProfileForm(formdata=None, data={
            'bio': author.bio,
            'contacts': [
                {'name': c.name, 'value': c.value}
                for c in contacts
            ] + [{'name': '', 'value': ''}]
        })
        if not has_avatar:
            del profile_form.delete_avatar
        if not avatar_uploading:
            del profile_form.avatar
    if not email_form:
        email_form = AuthorEditEmailForm(formdata=None, data={'email': new_email or author.email})
    if not password_form:
        password_form = AuthorEditPasswordForm(formdata=None)
    if not prefs_form:
        prefs_form = AuthorEditPrefsForm(formdata=None, data={
                'excluded_categories': author.excluded_categories_list,
                'detail_view': author.detail_view,
                'nsfw': author.nsfw,
                'comments_per_page': (
                    author.comments_per_page
                    if author.comments_per_page is not None
                    else current_app.config['COMMENTS_COUNT']['page']
                ),
                'comments_maxdepth': (
                    author.comments_maxdepth
                    if author.comments_maxdepth is not None
                    else current_app.config['COMMENTS_TREE_MAXDEPTH']
                ),
                'comment_spoiler_threshold': (
                    author.comment_spoiler_threshold
                    if author.comment_spoiler_threshold is not None
                    else current_app.config['COMMENT_SPOILER_THRESHOLD']
                ),
                'header_mode': {'': 2, 'off': 0, 'l': 1, 'ls': 2}[author.header_mode],
            }
        )
    if not subs_form:
        silent_email = author.silent_email_list
        silent_tracker = author.silent_tracker_list
        subs_form = AuthorEditSubscriptionsForm(formdata=None, data={
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
    data.update({
        'profile_form': profile_form,
        'email_form': email_form,
        'new_email': new_email,
        'password_form': password_form,
        'prefs_form': prefs_form,
        'subs_form': subs_form,
        'profile_form_errors': [],
        'email_form_errors': email_form_errors,
        'password_form_errors': password_form_errors,
        'prefs_form_errors': [],
    })
    return render_template('author_profile_edit.html', **data)


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
            modified_by_user=current_user._get_current_object(),
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
        current_user._get_current_object(),
        email=request.form.get('email') == '1',
        tracker=request.form.get('tracker') == '1',
    )

    if request.form.get('short') == '1':
        return jsonify(success=True)
    return redirect(url_for('author.info', user_id=author.id))
