#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for
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
@bp.route('/<int:user_id>/', defaults={'comments_page': 1})
@bp.route('/<int:user_id>/comments/page/<int:comments_page>/')
@db_session
def info(user_id=None, comments_page=1):
    data = {}

    if user_id is None:
        if not current_user.is_authenticated:
            abort(403)
        author = current_user._get_current_object()
        comments_list = StoryComment.bl.select_by_story_author(author)
        comments_list = comments_list.order_by(StoryComment.id.desc())
        stories = author.stories.order_by(Story.first_published_at.desc(), Story.id.desc())
        contributing_stories = author.contributing_stories.order_by(Story.first_published_at.desc(), Story.id.desc())

        data['all_views'] = Story.bl.get_all_views_for_author(author)

        data['page_title'] = gettext('My cabinet')
        template = 'author_dashboard.html'
    else:
        author = Author.get(id=user_id)
        if not author:
            abort(404)
        comments_list = StoryComment.select(lambda x: x.author == author and not x.deleted and x.story_published)
        comments_list = comments_list.order_by(StoryComment.id.desc())
        data['page_title'] = gettext('Author: {author}').format(author=author.username)
        stories = Story.bl.select_by_author(author, for_user=current_user)
        stories = stories.order_by(Story.first_published_at.desc(), Story.id.desc())
        contributing_stories = None
        template = 'author_overview.html'

    comments_count = comments_list.count()
    series = author.series[:]
    paged = Paginator(
        number=comments_page,
        total=comments_count,
        per_page=current_app.config['COMMENTS_COUNT']['author_page'],
    )  # TODO: restore orphans?
    comments = paged.slice(comments_list)
    if not comments and comments_page != 1:
        abort(404)
    num_pages = paged.num_pages

    data.update({
        'author': author,
        'stories': stories,
        'contributing_stories': contributing_stories,
        'series': series,
        'comments': comments,
        'page_current': comments_page,
        'num_pages': num_pages,
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
                author.bl.update(prefs_form.data)
                data['prefs_ok'] = True

        if 'save_subs' in request.form:
            prefs_form = AuthorEditSubscriptionsForm()
            if prefs_form.validate_on_submit():
                author.bl.update_email_subscriptions({
                    'story_pubrequest': prefs_form.email_story_pubrequest.data,
                    'story_publish': prefs_form.email_story_publish.data,
                    'story_draft': prefs_form.email_story_draft.data,
                    'story_reply': prefs_form.email_story_reply.data,
                    'story_lreply': prefs_form.email_story_lreply.data,
                })
                author.bl.update_tracker_subscriptions({
                    'story_publish': prefs_form.tracker_story_publish.data,
                    'story_draft': prefs_form.tracker_story_draft.data,
                    'story_reply': prefs_form.tracker_story_reply.data,
                    'story_lreply': prefs_form.tracker_story_lreply.data,
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
                'comments_maxdepth': (
                    author.comments_maxdepth
                    if author.comments_maxdepth is not None
                    else current_app.config['COMMENTS_TREE_MAXDEPTH']
                ),
                'comment_spoiler_threshold': (
                    author.comment_spoiler_threshold
                    if author.comment_spoiler_threshold is not None
                    else current_app.config['COMMENT_SPOILER_THRESHOLD']
                )
            }
        )
    if not subs_form:
        silent_email = author.silent_email_list
        silent_tracker = author.silent_tracker_list
        subs_form = AuthorEditSubscriptionsForm(formdata=None, data={
            'email_story_pubrequest': 'story_pubrequest' not in silent_email,

            'email_story_publish': 'story_publish' not in silent_email,
            'tracker_story_publish': 'story_publish' not in silent_tracker,

            'email_story_draft': 'story_draft' not in silent_email,
            'tracker_story_draft': 'story_draft' not in silent_tracker,

            'email_story_reply': 'story_reply' not in silent_email,
            'tracker_story_reply': 'story_reply' not in silent_tracker,

            'email_story_lreply': 'story_lreply' not in silent_email,
            'tracker_story_lreply': 'story_lreply' not in silent_tracker,
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


@bp.route('/<int:user_id>/ban/', methods=('POST',))
@db_session
def ban(user_id):
    if current_user.is_staff:
        author = Author.get(id=user_id)
        if not author:
            abort(404)
        if author.id != current_user.id:
            author.is_active = not author.is_active
        return redirect(url_for('author.info', user_id=user_id))
    else:
        abort(403)
