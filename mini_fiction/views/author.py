#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, current_app, request, render_template, abort, redirect, url_for
from flask_babel import gettext
from flask_login import current_user, login_required, logout_user
from pony.orm import select, db_session

from mini_fiction.models import Author, Story, CoAuthorsStory, StoryComment, StoryView
from mini_fiction.utils.misc import Paginator
from mini_fiction.utils.views import cached_lists
from mini_fiction.forms.author import AuthorEditEmailForm, AuthorEditPasswordForm, AuthorEditProfileForm, AuthorEditPrefsForm

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
        comments_list = StoryComment.select(lambda x: not x.deleted and x.story in select(x.story for x in CoAuthorsStory if x.author == author))
        comments_list = comments_list.order_by(StoryComment.id.desc())
        stories = author.stories.order_by(Story.date.desc(), Story.id.desc())
        data['all_views'] = StoryView.select(lambda x: x.story in stories).count()  # TODO: optimize it
        data['page_title'] = gettext('My cabinet')
        template = 'author_dashboard.html'
    else:
        author = Author.get(id=user_id)
        if not author:
            abort(404)
        comments_list = StoryComment.select(lambda x: x.author == author and not x.deleted and x.story_published)
        comments_list = comments_list.order_by(StoryComment.id.desc())
        data['page_title'] = gettext('Author: {author}').format(author=author.username)
        stories = Story.accessible(current_user).filter(lambda x: x in select(y.story for y in CoAuthorsStory if y.author == author))
        stories = stories.order_by(Story.date.desc(), Story.id.desc())
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

    comment_spoiler_threshold = current_app.config['COMMENT_SPOILER_THRESHOLD']
    data.update({
        'author': author,
        'stories': stories,
        'series': series,
        'comments': comments,
        'page_current': comments_page,
        'num_pages': num_pages,
        'comments_count': comments_count,
        'comment_spoiler_threshold': comment_spoiler_threshold,
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
    data = {'page_title': gettext('Profile settings'), 'user': author}

    profile_form = None
    email_form = None
    password_form = None
    prefs_form = None

    password_form_errors = []
    email_form_errors = []

    if request.method == 'POST' and request.form:
        if 'save_password' in request.form:
            password_form = AuthorEditPasswordForm(request.form)
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
            profile_form = AuthorEditProfileForm(request.form)
            if profile_form.validate_on_submit():
                author.bl.update(profile_form.data)
                data['profile_ok'] = True

        if 'save_email' in request.form:
            email_form = AuthorEditEmailForm(request.form)
            if email_form.validate_on_submit():
                if not author.bl.authenticate(email_form.password.data):
                    email_form_errors.append(gettext('Password is incorrect'))
                else:
                    author.bl.update({'email': email_form.email.data})
                    data['email_ok'] = True

        if 'save_prefs' in request.form:
            prefs_form = AuthorEditPrefsForm(request.form)
            if prefs_form.validate_on_submit():
                author.bl.update(prefs_form.data)
                data['prefs_ok'] = True

    if not profile_form:
        profile_form = AuthorEditProfileForm(formdata=None, data={
            'bio': author.bio,
            'jabber': author.jabber,
            'skype': author.skype,
            'tabun': author.tabun,
            'forum': author.forum,
            'vk': author.vk
        })
    if not email_form:
        email_form = AuthorEditEmailForm(formdata=None, data={'email': author.email})
    if not password_form:
        password_form = AuthorEditPasswordForm(formdata=None)
    if not prefs_form:
        prefs_form = AuthorEditPrefsForm(formdata=None, data={
            'excluded_categories': author.excluded_categories_list,
            'detail_view': author.detail_view,
            'nsfw': author.nsfw}
        )
    data.update({
        'profile_form': profile_form,
        'email_form': email_form,
        'password_form': password_form,
        'prefs_form': prefs_form,
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
