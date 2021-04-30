#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unused-variable

import os
import re
import sys
import logging
import importlib
from datetime import datetime
from logging.handlers import SMTPHandler

import jinja2
import cachelib
from celery import Celery
from werkzeug.urls import iri_to_uri
from werkzeug.utils import import_string
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.exceptions import HTTPException
from flask import Flask, current_app, request, g, jsonify
from flask import json as flask_json
from flask import sessions as flask_sessions
import flask_babel
from flask_login import LoginManager, current_user
from flask.logging import default_handler
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_cors import CORS
from pony.flask import Pony

from mini_fiction import models  # pylint: disable=unused-import
from mini_fiction import database, tasks, context_processors, ratelimit
from mini_fiction.bl import init_bl
from mini_fiction.utils import frontend


__all__ = ['create_app']


class LazySecureCookieSession(flask_sessions.SecureCookieSession):
    # Flask-Login дёргает сессию, даже когда нет изменений
    # Таким образом спасаемся от ненужного обновления сессионной куки
    def __setitem__(self, key, value):
        if self.get(key) != value:
            super().__setitem__(key, value)


class LazySecureCookieSessionInterface(flask_sessions.SecureCookieSessionInterface):
    session_class = LazySecureCookieSession


def create_app():
    select_default_settings()
    config_obj = import_string(os.environ.get('MINIFICTION_SETTINGS'))

    app = Flask(
        __name__,
        static_folder=config_obj.STATIC_ROOT,
        static_url_path=config_obj.STATIC_URL,
    )
    app.config.from_object(config_obj)

    default_handler.setLevel(app.config['LOGLEVEL'])
    logging.basicConfig(level=app.config['LOGLEVEL'], format=app.config['LOGFORMAT'])

    app.session_interface = LazySecureCookieSessionInterface()

    if app.config['UMASK'] is not None:
        if isinstance(app.config['UMASK'], str):
            app.config['UMASK'] = int(app.config['UMASK'], 8)
        os.umask(app.config['UMASK'])

    if app.config['TESTING']:
        if not os.path.isdir(app.config['TESTING_DIRECTORY']):
            os.makedirs(app.config['TESTING_DIRECTORY'])
        elif os.listdir(app.config['TESTING_DIRECTORY']):
            raise RuntimeError('Testing directory %r is not empty' % app.config['TESTING_DIRECTORY'])

    # Flask's after_request/teardown_request hooks are executed in the reversed
    # order of their declaration. after_request_callbacks must be executed
    # outside of the db_session context (after commit), so attach it before Pony ORM
    configure_after_request_callbacks(app)

    Pony(app)  # binds db_session to before_request/teardown_request

    init_bl()

    configure_user_agent(app)
    configure_i18n(app)
    configure_cache(app)
    configure_rate_limit(app)
    configure_forms(app)
    configure_users(app)
    configure_error_handlers(app)
    configure_views(app)
    configure_admin_views(app)
    configure_staticfiles(app)
    configure_ajax(app)
    configure_errorpages(app)
    configure_templates(app)
    if not app.config['SPHINX_DISABLED']:
        configure_search(app)
    configure_celery(app)
    configure_captcha(app)
    configure_story_voting(app)
    configure_misc(app)
    configure_development(app)
    configure_frontend(app)
    configure_sidebar(app)

    app.context_processor(templates_context)

    init_plugins(app)
    database.configure_for_app(app)
    CORS(app, resources={r"/static/*": {"origins": "*"}})

    return app


def select_default_settings():
    if os.environ.get('MINIFICTION_SETTINGS'):
        return

    if os.path.isfile(os.path.join(os.getcwd(), 'local_settings.py')):
        os.environ.setdefault(
            'MINIFICTION_SETTINGS',
            'local_settings.Test' if os.environ.get('FLASK_ENV') == 'test' else 'local_settings.Local'
        )

    elif os.environ.get('FLASK_ENV') == 'test':  # see tests/conftest.py
        os.environ.setdefault('MINIFICTION_SETTINGS', 'mini_fiction.settings.Test')

    elif os.environ.get('FLASK_ENV') == 'development':  # uses .env file if started by mini_fiction command
        os.environ.setdefault('MINIFICTION_SETTINGS', 'mini_fiction.settings.Development')

    else:
        os.environ.setdefault('MINIFICTION_SETTINGS', 'mini_fiction.settings.Config')


def configure_after_request_callbacks(app):
    # We have to use teardown_request instead of after_request because Pony ORM uses it
    @app.teardown_request
    def call_after_request_callbacks(exc=None):
        if exc is not None:
            return
        for f, args, kwargs in getattr(g, 'after_request_callbacks', ()):
            f(*args, **kwargs)


def configure_user_agent(app):
    # pylint: disable=E1101

    if app.config.get('USER_AGENT'):
        app.user_agent = str(app.config.get('USER_AGENT'))
        return

    import platform
    import urllib.request as urequest

    import mini_fiction

    context = {
        'system': platform.system() or 'NA',
        'machine': platform.machine() or 'NA',
        'release': platform.release() or 'NA',
        'pyi': platform.python_implementation() or 'Python',
        'pyv': platform.python_version(),
        'pyiv': platform.python_version(),
        'urv': urequest.__version__,
        'mfv': mini_fiction.__version__,
    }
    if context['pyi'] == 'PyPy':
        context['pyiv'] = '{}.{}.{}'.format(
            sys.pypy_version_info.major,
            sys.pypy_version_info.minor,
            sys.pypy_version_info.micro,
        )
        if sys.pypy_version_info.releaselevel != 'final':
            context['pyiv'] = context['pyiv'] + sys.pypy_version_info.releaselevel

    app.user_agent = (
        'mini_fiction/{mfv} ({system} {machine} {release}) '
        'Python/{pyv} {pyi}/{pyiv} urllib/{urv}'
    ).format(**context)

    postfix = None
    if app.config.get('USER_AGENT_POSTFIX'):
        postfix = str(app.config.get('USER_AGENT_POSTFIX')).strip()
    if postfix:
        app.user_agent += ' ' + postfix


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

    @babel.timezoneselector
    def get_timezone():
        if not request:
            if hasattr(g, 'timezone'):
                return g.timezone
            raise RuntimeError('Babel is used outside of request context, please set g.timezone')
        return current_user.timezone or None

    @app.before_request
    def before_request():
        g.locale = flask_babel.get_locale()
        g.timezone = flask_babel.get_timezone()


def configure_cache(app):
    kwargs = dict(app.config['CACHE_PARAMS'])

    cache_class = 'cachelib.base.NullCache'
    cache_type = app.config['CACHE_TYPE']

    if cache_type == 'memcached':
        cache_class = 'cachelib.memcached.MemcachedCache'
    elif cache_type == 'redis':
        cache_class = 'cachelib.redis.RedisCache'
    elif cache_type == 'filesystem':
        cache_class = 'cachelib.file.FileSystemCache'
    elif cache_type == 'uwsgi':
        cache_class = 'cachelib.uwsgi.UWSGICache'
    elif cache_type == 'simple':
        cache_class = 'cachelib.simple.SimpleCache'
    elif '.' in cache_type:
        cache_class = cache_type
    elif cache_type != 'null':
        raise ValueError(f'Unknown cache type: {cache_type!r}')

    app.cache = import_string(cache_class)(**kwargs)


def configure_rate_limit(app):
    if app.config.get('RATE_LIMIT_BACKEND'):
        app.rate_limiter = ratelimit.RedisRateLimiter(app)
    else:
        app.rate_limiter = ratelimit.NullRateLimiter(app)


def configure_forms(app):
    app.csrf = CSRFProtect(app)


def configure_users(app):
    app.login_manager = LoginManager(app)
    app.login_manager.login_view = 'auth.login'
    app.login_manager.anonymous_user = models.AnonymousUser

    @app.login_manager.user_loader
    def load_user(token):
        try:
            user_id = token.split('#', 1)[0]
        except Exception:
            return

        user = models.Author.get(id=user_id, is_active=1)
        if not user or user.get_id() != token:
            return

        if user.id != current_app.config['SYSTEM_USER_ID']:
            tm = datetime.utcnow()
            if not user.last_visit or (tm - user.last_visit).total_seconds() >= 60:
                user.last_visit = tm

        return user


def templates_context():
    context = {}
    context.update(current_app.templatetags)
    for c in context_processors.context_processors:
        context.update(c() or {})
    return context


def configure_error_handlers(app):
    class RequestErrorFormatter(logging.Formatter):
        def format(self, record):
            from pony.orm import db_session

            record.remote_addr = request.remote_addr
            with db_session:
                record.user_id = current_user.id if current_user.is_authenticated else None
                record.username = current_user.username if current_user.is_authenticated else None

            return super().format(record)

    if app.config['ADMINS'] and app.config['ERROR_EMAIL_HANDLER_PARAMS']:
        params = dict(app.config['ERROR_EMAIL_HANDLER_PARAMS'])
        params['toaddrs'] = app.config['ADMINS']
        params['fromaddr'] = app.config['ERROR_EMAIL_FROM']
        params['subject'] = app.config['ERROR_EMAIL_SUBJECT']
        smtp_handler = SMTPHandler(**params)
        smtp_handler.setLevel(logging.ERROR)
        smtp_handler.setFormatter(RequestErrorFormatter(app.config['ERROR_LOGFORMAT']))
        app.logger.addHandler(smtp_handler)


def configure_views(app):
    from mini_fiction.views import index, auth, story, chapter, editlog, search, author, stream, object_lists
    from mini_fiction.views import story_comment, story_local_comment, feeds, staticpages, news, news_comment
    from mini_fiction.views import notifications, abuse, sitemap, tags
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
    app.register_blueprint(abuse.bp, url_prefix='/abuse')
    app.register_blueprint(sitemap.bp)
    app.register_blueprint(tags.bp)

    app.add_url_rule('/dump/', 'dump', misc.dump)


def configure_admin_views(app):
    from mini_fiction.views.admin import index, characters, charactergroups
    from mini_fiction.views.admin import logopics, htmlblocks, staticpages, news, abuse_reports, votes
    from mini_fiction.views.admin import authors, registrations, tag_categories, tags

    app.register_blueprint(index.bp, url_prefix='/admin')
    app.register_blueprint(logopics.bp, url_prefix='/admin/logopics')
    app.register_blueprint(htmlblocks.bp, url_prefix='/admin/htmlblocks')
    app.register_blueprint(characters.bp, url_prefix='/admin/characters')
    app.register_blueprint(charactergroups.bp, url_prefix='/admin/charactergroups')
    app.register_blueprint(staticpages.bp, url_prefix='/admin/staticpages')
    app.register_blueprint(news.bp, url_prefix='/admin/news')
    app.register_blueprint(abuse_reports.bp, url_prefix='/admin/abuse_reports')
    app.register_blueprint(votes.bp, url_prefix='/admin/votes')
    app.register_blueprint(authors.bp, url_prefix='/admin/authors')
    app.register_blueprint(registrations.bp, url_prefix='/admin/registrations')
    app.register_blueprint(tag_categories.bp, url_prefix='/admin/tag_categories')
    app.register_blueprint(tags.bp, url_prefix='/admin/tags')


def configure_staticfiles(app):
    from mini_fiction.views import misc

    app.extra_css = []
    app.extra_js = []

    app.add_url_rule('/{}/<path:filename>'.format(app.config['MEDIA_URL'].strip('/')), 'media', misc.media)
    if app.config['LOCALSTATIC_ROOT']:
        app.add_url_rule('/{}/<path:filename>'.format(app.config['LOCALSTATIC_URL'].strip('/')), 'localstatic', misc.localstatic)

    # Static invalidation
    app.static_v = None
    if app.config.get('STATIC_V'):
        app.static_v = app.config['STATIC_V']
    elif app.config.get('STATIC_ROOT') and app.config.get('STATIC_VERSION_FILE'):
        version_file_path = os.path.join(app.config['STATIC_ROOT'], app.config['STATIC_VERSION_FILE'])
        if os.path.isfile(version_file_path):
            with open(version_file_path, 'r', encoding='utf-8') as fp:
                app.static_v = fp.read().strip()

    @app.url_defaults
    def static_postfix(endpoint, values):
        if endpoint in ('static', 'localstatic') and 'v' not in values and not values['filename'].startswith('build/') and app.static_v:
            values['v'] = app.static_v


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
        if not response.direct_passthrough and response.data and response.data.startswith(b'{') and response.content_type == 'text/html; charset=utf-8':
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

    def _error_common(template, template_modal, code, e):
        # g.is_ajax здесь не всегда присутствует, так что так
        is_ajax = request.headers.get('X-AJAX') == '1' or request.args.get('isajax') == '1'
        if is_ajax:
            html = render_template(template_modal, error=e, error_code=code)
            response = jsonify({'page_content': {'modal': html}})
            response.status_code = code
            # for github-fetch polyfill:
            response.headers['X-Request-URL'] = iri_to_uri(request.url)
            return response

        html = render_template(template, error=e, error_code=code)
        return html, code

    def _page403(e):
        return _error_common('403.html', '403_modal.html', 403, e)

    def _page404(e):
        return _error_common('404.html', '404_modal.html', 404, e)

    def _page500(e):
        return _error_common('500.html', '500_modal.html', 500, e)

    def _page_rate_limit(e):
        response = _error_common('rate_limit.html', 'rate_limit_modal.html', 429, e)
        if e.ttl > 0:
            response.headers['Retry-After'] = str(e.ttl)
        return response

    def _pagecsrf(e):
        return _error_common('csrf.html', 'csrf_modal.html', 400, e)

    def _pageall(e):
        if e.code and e.code < 400:
            return e
        return _error_common('error.html', 'error_modal.html', e.code or 500, e)

    app.errorhandler(403)(_page403)
    app.errorhandler(404)(_page404)
    app.errorhandler(500)(_page500)
    app.errorhandler(ratelimit.RateLimitExceeded)(_page_rate_limit)
    app.errorhandler(CSRFError)(_pagecsrf)
    app.errorhandler(HTTPException)(_pageall)


def configure_templates(app):
    from mini_fiction.templatetags import random_stories, logopic, submitted_stories_count
    from mini_fiction.templatetags import story_comments_delta, html_block, hook, shown_newsitem
    from mini_fiction.templatetags import get_comment_threshold, notifications, misc
    from mini_fiction.templatetags import i18n, generate_captcha, unread_abuse_reports_count
    from mini_fiction.templatetags import registry
    app.templatetags = dict(registry.tags)

    app.jinja_env.filters['tojson_raw'] = flask_json.dumps  # not escapes &, < and >

    if app.config['LOCALTEMPLATES']:
        paths = app.config['LOCALTEMPLATES']
        if isinstance(paths, str):
            paths = [paths]

        loaders = []
        for x in paths:
            loaders.append(jinja2.FileSystemLoader(os.path.abspath(x)))
        loaders.append(app.jinja_loader)

        app.jinja_loader = jinja2.ChoiceLoader(loaders)

    from mini_fiction.templatefilters import timesince
    from mini_fiction.templatefilters import registry as filters_registry

    app.jinja_env.filters.update(filters_registry.filters)


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


def configure_captcha(app):
    captcha_path = app.config.get('CAPTCHA_CLASS')
    if not captcha_path or '.' not in captcha_path:
        app.captcha = None
        return

    module, cls = captcha_path.rsplit('.', 1)
    Captcha = getattr(importlib.import_module(module), cls)
    del module, cls

    app.captcha = Captcha(app)


def configure_story_voting(app):
    story_voting_path = app.config.get('STORY_VOTING_CLASS')
    if not story_voting_path or '.' not in story_voting_path:
        app.story_voting = None
        return

    module, cls = story_voting_path.rsplit('.', 1)
    StoryVoting = getattr(importlib.import_module(module), cls)
    del module, cls

    app.story_voting = StoryVoting(app)


def configure_misc(app):
    @app.after_request
    def disable_cache(response):
        if not getattr(response, 'cache_control_exempt', False):
            response.cache_control.max_age = 0
            response.cache_control.private = True
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


def configure_frontend(app: Flask):
    app.add_template_global(
        frontend.webpack_asset,
        name='webpack_asset'
    )


def configure_sidebar(app: Flask):
    app.index_sidebar = {}

    for block_name, func_path in app.config['INDEX_SIDEBAR'].items():
        if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', block_name):
            raise ValueError('Invalid sidebar block name: {!r}'.format(block_name))

        module_name, func_name = func_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        app.index_sidebar[block_name] = func


def init_plugins(app):
    app.plugins = []
    app.hooks = {}
    with app.app_context():
        for plugin_module in app.config['PLUGINS']:
            if ':' in plugin_module:
                plugin_module, func_name = plugin_module.split(':', 1)
            else:
                func_name = 'configure_app'
            plugin = importlib.import_module(plugin_module)
            app.plugins.append(plugin)
            getattr(plugin, func_name)(register_hook)


def register_hook(name, func):
    if 'name' not in current_app.hooks:
        current_app.hooks[name] = []
    current_app.hooks[name].append(func)
