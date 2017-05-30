#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unused-variable

import os
import logging
import importlib
from datetime import datetime
from logging.handlers import SMTPHandler

import jinja2
from celery import Celery
from werkzeug.urls import iri_to_uri
from werkzeug.contrib import cache
from werkzeug.contrib.fixers import ProxyFix
from flask import Flask, current_app, request, g, jsonify
from flask import json as flask_json
import flask_babel
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from mini_fiction import models  # pylint: disable=unused-import
from mini_fiction import database, tasks
from mini_fiction.bl import init_bl
from mini_fiction.utils.misc import sitename


__all__ = ['create_app']


def create_app():
    if os.path.isfile(os.path.join(os.getcwd(), 'local_settings.py')):
        os.environ.setdefault('MINIFICTION_SETTINGS', 'local_settings.Local')
    else:
        os.environ.setdefault('MINIFICTION_SETTINGS', 'mini_fiction.settings.Development')

    app = Flask(__name__)
    app.config.from_object(os.environ.get('MINIFICTION_SETTINGS'))
    app.static_folder = app.config['STATIC_ROOT']
    init_bl()

    configure_i18n(app)
    configure_cache(app)
    configure_forms(app)
    configure_users(app)
    configure_error_handlers(app)
    configure_views(app)
    configure_admin_views(app)
    configure_ajax(app)
    configure_errorpages(app)
    configure_templates(app)
    if not app.config['SPHINX_DISABLED']:
        configure_search(app)
    configure_celery(app)
    configure_misc(app)
    configure_development(app)

    app.context_processor(templates_context)

    init_plugins(app)
    database.configure_for_app(app)

    return app


def configure_i18n(app):
    babel = flask_babel.Babel(app)

    @babel.localeselector
    def get_locale():
        if not request:
            if hasattr(g, 'locale'):
                return g.locale
            raise RuntimeError('Babel is used outside of request context, please set g.locale')
        locales = app.config['LOCALES'].keys()
        locale = request.cookies.get('locale')
        if locale in locales:
            return locale
        return request.accept_languages.best_match(locales)

    @app.before_request
    def before_request():
        g.locale = flask_babel.get_locale()


def configure_cache(app):
    if app.config.get('MEMCACHE_SERVERS'):
        app.cache = cache.MemcachedCache(app.config['MEMCACHE_SERVERS'], key_prefix=app.config.get('CACHE_PREFIX', ''))
    else:
        app.cache = cache.NullCache()


def configure_forms(app):
    app.csrf = CSRFProtect(app)


def configure_users(app):
    app.login_manager = LoginManager(app)
    app.login_manager.login_view = 'auth.login'
    app.login_manager.anonymous_user = models.AnonymousUser

    @app.login_manager.user_loader
    def load_user(user_id):
        user = models.Author.get(id=int(user_id), is_active=1)
        if not user:
            return

        tm = datetime.utcnow()
        if not user.last_visit or (tm - user.last_visit).total_seconds() >= 60:
            user.last_visit = tm

        return user


def templates_context():
    context = {}
    context.update(current_app.templatetags)
    context.update({
        'SITE_NAME': sitename(),
        'base': current_app.jinja_env.get_template('base.json' if getattr(g, 'is_ajax', False) else 'base.html'),
        'contact_types': {x['name']: x for x in current_app.config['CONTACTS']},
    })
    return context


def configure_error_handlers(app):
    if app.config['ADMINS'] and app.config['ERROR_EMAIL_HANDLER_PARAMS']:
        params = dict(app.config['ERROR_EMAIL_HANDLER_PARAMS'])
        params['toaddrs'] = app.config['ADMINS']
        params['fromaddr'] = app.config['ERROR_EMAIL_FROM']
        params['subject'] = app.config['ERROR_EMAIL_SUBJECT']
        handler = SMTPHandler(**params)
        handler.setLevel(logging.ERROR)
        app.logger.addHandler(handler)


def configure_views(app):
    from mini_fiction.views import index, auth, story, chapter, editlog, search, author, stream, object_lists
    from mini_fiction.views import story_comment, story_local_comment, feeds, staticpages, news, news_comment
    from mini_fiction.views import notifications
    from mini_fiction.views import misc
    app.register_blueprint(index.bp)
    app.register_blueprint(auth.bp, url_prefix='/accounts')
    app.register_blueprint(story.bp, url_prefix='/story')
    app.register_blueprint(chapter.bp)  # /story/%d/chapter/* and /chapter/*
    app.register_blueprint(editlog.bp, url_prefix='/editlog')
    app.register_blueprint(search.bp, url_prefix='/search')
    app.csrf.exempt(search.bp)
    app.register_blueprint(author.bp, url_prefix='/accounts')
    app.register_blueprint(stream.bp, url_prefix='/stream')
    app.register_blueprint(object_lists.bp)
    app.register_blueprint(story_comment.bp)
    app.register_blueprint(story_local_comment.bp)
    app.register_blueprint(feeds.bp, url_prefix='/feeds')
    app.register_blueprint(staticpages.bp)
    app.register_blueprint(news.bp, url_prefix='/news')
    app.register_blueprint(news_comment.bp)
    app.register_blueprint(notifications.bp, url_prefix='/notifications')

    app.add_url_rule('/media/<path:filename>', 'media', misc.media)
    if app.config['LOCALSTATIC_ROOT']:
        app.add_url_rule('/localstatic/<path:filename>', 'localstatic', misc.localstatic)

    # Static invalidation
    @app.url_defaults
    def static_postfix(endpoint, values):
        if endpoint in ('static', 'localstatic') and 'v' not in values and 'STATIC_V' in app.config:
            values['v'] = app.config['STATIC_V']


def configure_admin_views(app):
    from mini_fiction.views.admin import index, categories, characters, charactergroups, classifications
    from mini_fiction.views.admin import htmlblocks, staticpages, authors, news
    app.register_blueprint(index.bp, url_prefix='/admin')
    app.register_blueprint(htmlblocks.bp, url_prefix='/admin/htmlblocks')
    app.register_blueprint(categories.bp, url_prefix='/admin/categories')
    app.register_blueprint(characters.bp, url_prefix='/admin/characters')
    app.register_blueprint(charactergroups.bp, url_prefix='/admin/charactergroups')
    app.register_blueprint(classifications.bp, url_prefix='/admin/classifications')
    app.register_blueprint(staticpages.bp, url_prefix='/admin/staticpages')
    app.register_blueprint(authors.bp, url_prefix='/admin/authors')
    app.register_blueprint(news.bp, url_prefix='/admin/news')


def configure_ajax(app):
    @app.before_request
    def is_request_ajax():
        g.is_ajax = request.headers.get('X-AJAX') == '1' or request.args.get('isajax') == '1'

    @app.after_request
    def ajax_template_response(response):
        if response.headers.get('Vary'):
            response.headers['Vary'] = 'X-AJAX, ' + response.headers['Vary']
        else:
            response.headers['Vary'] = 'X-AJAX'
        if not getattr(g, 'is_ajax', False):
            return response
        if response.data and response.data.startswith(b'{') and response.content_type == 'text/html; charset=utf-8':
            response.content_type = 'application/json'
            # for github-fetch polyfill:
            response.headers['X-Request-URL'] = iri_to_uri(request.url)
        elif response.status_code == 302:
            # Люблю разрабов js во всех смыслах
            response.data = flask_json.dumps({'page_content': {'redirect': response.headers.get('Location')}})
            response.content_type = 'application/json'
            response.status_code = 200
        return response


def configure_errorpages(app):
    from flask import render_template
    from pony.orm import db_session

    def _error_common(template, template_modal, code, e):
        if getattr(g, 'is_ajax', False):
            html = render_template(template_modal, error=e, error_code=code)
            response = jsonify({'page_content': {'modal': html}})
            response.status_code = code
            # for github-fetch polyfill:
            response.headers['X-Request-URL'] = iri_to_uri(request.url)
            return response
        else:
            html = render_template(template, error=e, error_code=code)
            return html, code

    def _page403(e):
        return _error_common('403.html', '403_modal.html', 403, e)

    def _page404(e):
        return _error_common('404.html', '404_modal.html', 404, e)

    def _page500(e):
        return _error_common('500.html', '500_modal.html', 500, e)

    def _pageall(e):
        return _error_common('error.html', 'error_modal.html', e.code or 500, e)

    app.errorhandler(403)(db_session(_page403))
    app.errorhandler(404)(db_session(_page404))
    app.errorhandler(500)(db_session(_page500))

    # Здесь должно было быть HTTPException, но https://github.com/mitsuhiko/flask/issues/941
    app.errorhandler(405)(db_session(_pageall))


def configure_templates(app):
    from mini_fiction.templatetags import random_stories, random_logo, submitted_stories_count
    from mini_fiction.templatetags import story_comments_delta, html_block, hook, shown_newsitem
    from mini_fiction.templatetags import get_comment_threshold, notifications, misc
    from mini_fiction.templatetags import i18n
    from mini_fiction.templatetags import registry
    app.templatetags = dict(registry.tags)

    app.jinja_env.filters['tojson_raw'] = flask_json.dumps  # not escapes &, < and >

    if app.config['LOCALTEMPLATES']:
        my_loader = jinja2.ChoiceLoader([
            jinja2.FileSystemLoader(os.path.abspath(app.config['LOCALTEMPLATES'])),
            app.jinja_loader,
        ])
        app.jinja_loader = my_loader


def configure_search(app):
    from mini_fiction.apis import amsphinxql
    app.sphinx = amsphinxql.SphinxPool(app.config['SPHINX_CONFIG']['connection_params'])


def configure_celery(app):
    app.celery = Celery('mini_fiction', broker=app.config['CELERY_CONFIG']['broker_url'])
    app.celery.conf.update(app.config['CELERY_CONFIG'])

    TaskBase = app.celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    app.celery.Task = ContextTask

    tasks.apply_for_app(app)


def configure_misc(app):
    @app.after_request
    def after_request(response):
        response.cache_control.max_age = 0

        for f, args, kwargs in getattr(g, 'after_request_callbacks', ()):
            f(*args, **kwargs)
        return response

    # Pass proxies for correct request_addr
    if app.config['PROXIES_COUNT'] > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, app.config['PROXIES_COUNT'])


def configure_development(app):
    if app.config.get('DEBUG_TB_ENABLED'):
        import time
        from flask_debugtoolbar import DebugToolbarExtension
        DebugToolbarExtension(app)

        if (
            'mini_fiction.utils.debugtoolbar.PonyDebugPanel' in app.config.get('DEBUG_TB_PANELS', ()) and
            (app.debug or app.config.get('PONYORM_RECORD_QUERIES'))
        ):
            from mini_fiction.utils import debugtoolbar as ponydbg
            from flask_debugtoolbar import module

            old_exec_sql = database.db._exec_sql

            def my_exec_sql(sql, arguments=None, *args, **kwargs):
                t = time.time()
                result = old_exec_sql(sql, arguments, *args, **kwargs)
                t = time.time() - t
                ponydbg.record_query({
                    'statement': sql,
                    'parameters': arguments or (),
                    'duration': t,
                })
                return result
            database.db._exec_sql = my_exec_sql

            app.before_request(ponydbg.clear_queries)
            app.csrf.exempt(module)


def init_plugins(app):
    app.hooks = {}
    with app.app_context():
        for plugin_module in app.config['PLUGINS']:
            if ':' in plugin_module:
                plugin_module, func_name = plugin_module.split(':', 1)
            else:
                func_name = 'configure_app'
            plugin = importlib.import_module(plugin_module)
            getattr(plugin, func_name)(register_hook)


def register_hook(name, func):
    if 'name' not in current_app.hooks:
        current_app.hooks[name] = []
    current_app.hooks[name].append(func)
