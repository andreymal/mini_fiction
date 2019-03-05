#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, url_for, redirect, request
from flask_babel import gettext
from flask_login import current_user
from pony.orm import db_session

from mini_fiction.utils.views import admin_required
from mini_fiction.validation import ValidationError
from mini_fiction.forms.admin.tag import TagForm
from mini_fiction.models import Tag, TagCategory
from mini_fiction.utils.views import admin_sort
from mini_fiction.utils.misc import Paginator, normalize_tag

bp = Blueprint('admin_tags', __name__)


@bp.route('/page/last/', defaults={'page': -1})
@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>/')
@db_session
@admin_required
def index(page):
    objects = Tag.select().order_by(Tag.iname)

    args = {
        'page': page,
        'sorting': request.args.get('sorting') or 'iname',
    }

    if request.args.get('name'):
        iname = normalize_tag(request.args['name'])
        args['name'] = iname
        objects = objects.filter(lambda x: iname in x.iname)

    if request.args.get('category'):
        if request.args['category'] == '0':
            args['category'] = '0'
            objects = objects.filter(lambda x: x.category is None)
        elif request.args['category'].isdigit():
            args['category'] = request.args['category']
            cat_id = int(request.args['category'])
            objects = objects.filter(lambda x: x.category.id == cat_id)

    if request.args.get('is_blacklisted') == '0':
        args['is_blacklisted'] = '0'
        objects = objects.filter(lambda x: not x.is_blacklisted)
    elif request.args.get('is_blacklisted') == '1':
        args['is_blacklisted'] = '1'
        objects = objects.filter(lambda x: x.is_blacklisted)

    if request.args.get('is_alias') == '0':
        args['is_alias'] = '0'
        objects = objects.filter(lambda x: not x.is_alias)
    elif request.args.get('is_alias') == '1':
        args['is_alias'] = '1'
        objects = objects.filter(lambda x: x.is_alias)

    if request.args.get('is_main_tag') == '0':
        args['is_main_tag'] = '0'
        objects = objects.filter(lambda x: not x.is_main_tag)
    elif request.args.get('is_main_tag') == '1':
        args['is_main_tag'] = '1'
        objects = objects.filter(lambda x: x.is_main_tag)

    objects = objects.prefetch(Tag.is_alias_for, Tag.created_by, Tag.category)

    objects = admin_sort(args['sorting'], objects, {
        'iname': Tag.iname,
        'created_at': (Tag.created_at, Tag.id),
        'stories_count': (Tag.stories_count, Tag.id),
    }, default='iname')

    page_obj = Paginator(page, objects.count(), per_page=100, endpoint=request.endpoint, view_args=args)

    return render_template(
        'admin/tags/index.html',
        tags=page_obj.slice_or_404(objects),
        page_obj=page_obj,
        page_title=gettext('Tags'),
        endpoint=request.endpoint,
        args=args,
        tag_categories=list(TagCategory.select().order_by(TagCategory.id)),
    )


@bp.route('/create/', methods=('GET', 'POST'))
@db_session
@admin_required
def create():
    form = TagForm()

    if form.validate_on_submit():
        data = dict(form.data)
        if data.get('category') == 0:
            data['category'] = None
        try:
            tag = Tag.bl.create(current_user._get_current_object(), data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            return redirect(url_for('admin_tags.update', pk=tag.id))

    return render_template(
        'admin/tags/work.html',
        page_title=gettext('Create'),
        form=form,
        edit=False,
    )


@bp.route('/<pk>/', methods=('GET', 'POST'))
@db_session
@admin_required
def update(pk):
    if not pk.isdigit():
        iname = normalize_tag(pk)
        if not iname:
            abort(404)
        tag = Tag.get(iname=iname)
        if not tag:
            abort(404)
        return redirect(url_for('admin_tags.update', pk=str(tag.id)))

    pk = int(pk)
    tag = Tag.get(id=pk)
    if not tag:
        abort(404)

    form = TagForm(data={
        'name': tag.name,
        'category': tag.category.id if tag.category else 0,
        'color': tag.color,
        'description': tag.description,
        'is_main_tag': tag.is_main_tag,
        'is_alias_for': tag.is_alias_for.name if tag.is_alias_for else '',
        'is_hidden_alias': tag.is_hidden_alias,
        'reason_to_blacklist': tag.reason_to_blacklist,
    })

    saved = False

    if form.validate_on_submit():
        data = dict(form.data)
        if data.get('category') == 0:
            data['category'] = None
        try:
            tag.bl.update(current_user._get_current_object(), data)
        except ValidationError as exc:
            form.set_errors(exc.errors)
        else:
            saved = True

    tag_aliases = Tag.select(lambda x: x.is_alias_for == tag)
    visible_tag_aliases = [x for x in tag_aliases if not x.is_hidden_alias]
    hidden_tag_aliases = [x for x in tag_aliases if x.is_hidden_alias]

    return render_template(
        'admin/tags/work.html',
        page_title=tag.name,
        tag=tag,
        visible_tag_aliases=visible_tag_aliases,
        hidden_tag_aliases=hidden_tag_aliases,
        form=form,
        edit=True,
        saved=saved,
    )
