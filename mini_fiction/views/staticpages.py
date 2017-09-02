#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, Markup, Response, request, current_app, render_template, g, abort, jsonify
from pony.orm import db_session

from mini_fiction.models import StaticPage

bp = Blueprint('staticpages', __name__)


@bp.route('/robots.txt', defaults={'name': 'robots.txt'})
@bp.route('/page/<path:name>/')
@db_session
def index(name):
    page = StaticPage.get(name=name, lang=g.locale.language)
    if not page:
        page = StaticPage.get(name=name, lang='none')
    if not page:
        abort(404)

    if page.is_template:
        template = current_app.jinja_env.from_string(page.content)
        template.name = 'db/staticpages/{}.html'.format(name)
        content = render_template(template, page_name=page.name, page_title=page.title)
    else:
        content = page.content

    if page.is_full_page:
        if g.is_ajax:
            return jsonify({'page_content': {'full_link': request.url}})
        return Response(content, mimetype=page.bl.get_mimetype())
    else:
        return render_template('staticpage.html', content=Markup(content), page_name=page.name, page_title=page.title)
