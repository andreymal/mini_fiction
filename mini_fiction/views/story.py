from io import StringIO
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, current_app, request, render_template, abort, redirect, url_for, send_file, jsonify, g
from flask_babel import gettext
from flask_login import current_user, login_required
from pony.orm import db_session

from mini_fiction.bl.migration import enrich_story
from mini_fiction.forms.story import StoryForm
from mini_fiction.forms.comment import CommentForm
from mini_fiction.models import Author, Story, Chapter, Rating, StoryLog, Favorites, Bookmark, Subscription
from mini_fiction.validation import ValidationError
from mini_fiction.utils.misc import calc_maxdepth
from mini_fiction.views.editlog import load_users_for_editlog

bp = Blueprint('story', __name__)


def get_story(pk, for_update=False):
    if for_update:
        story = Story.get_for_update(id=pk)
    else:
        story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.bl.has_access(current_user):
        abort(403)
    return story


@bp.route('/<int:pk>/', defaults={'comments_page': -1})
@bp.route('/<int:pk>/comments/page/<int:comments_page>/')
@db_session
def view(pk, comments_page):
    story = get_story(pk)

    per_page = current_user.comments_per_page or current_app.config['COMMENTS_COUNT']['page']
    maxdepth = None if request.args.get('fulltree') == '1' else calc_maxdepth(current_user)

    last_viewed_comment = story.bl.last_viewed_comment_by(current_user)
    comments_count, paged, comments_tree_list = story.bl.paginate_comments(comments_page, per_page, maxdepth, last_viewed_comment=last_viewed_comment)
    if not comments_tree_list and paged.number != 1:
        abort(404)

    act = story.bl.get_activity(current_user)

    local_comments_count = 0
    new_local_comments_count = 0
    if story.local and ((current_user and current_user.is_staff) or story.bl.is_contributor(current_user)):
        local_comments_count = story.bl.get_or_create_local_thread().comments_count
        new_local_comments_count = (
            (story.bl.get_or_create_local_thread().comments_count - act.last_local_comments)
            if act else 0
        )

    chapters = list(story.chapters.select().order_by(Chapter.order, Chapter.id))
    if not current_user.is_staff and not story.bl.is_contributor(current_user):
        chapters = [x for x in chapters if not x.draft]

    show_first_chapter = len(chapters) == 1 and not chapters[0].draft

    if current_user.is_authenticated:
        story.bl.viewed(current_user)
        if show_first_chapter:
            chapters[0].bl.viewed(current_user)
        user_vote = story.votes.select(lambda x: x.author == current_user).first()
    else:
        user_vote = None

    comment_ids = [x[0].id for x in comments_tree_list]
    if current_user.is_authenticated:
        comment_votes_cache = story.bl.select_comment_votes(current_user, comment_ids)
    else:
        comment_votes_cache = {i: 0 for i in comment_ids}

    chapter_subscriptions_count = Subscription.select().filter(
        lambda x: x.type == 'story_chapter' and x.target_id == story.id
    ).count()

    enrich_story(story)

    data = {
        'story': story,
        'contributors': story.bl.get_contributors_for_view(),
        'vote': user_vote,
        'author_ids': [x.id for x in story.authors],
        'comments_tree_list': comments_tree_list,
        'comments_count': comments_count,
        'comment_votes_cache': comment_votes_cache,
        'last_viewed_comment': last_viewed_comment,
        'local_comments_count': local_comments_count,
        'new_local_comments_count': new_local_comments_count,
        'chapters': chapters,
        'show_first_chapter': show_first_chapter,
        'page_title': story.title,
        'comment_form': CommentForm(),
        'page_obj': paged,
        'sub': story.bl.get_subscription(current_user),
        'sub_comments': story.bl.get_comments_subscription(current_user),
        'robots_noindex': not story.published or story.robots_noindex,
        'favorites_count': story.favorites.select().count(),
        'show_meta_description': comments_page == -1,
        'chapter_subscriptions_count': chapter_subscriptions_count,
    }

    return render_template('story_view.html', **data)


@bp.route('/<int:pk>/subscribe/', methods=('POST',))
@db_session
@login_required
def subscribe(pk):
    story = get_story(pk)
    story.bl.subscribe(
        current_user,
        email=request.form.get('email') == '1',
        tracker=request.form.get('tracker') == '1',
    )

    if request.form.get('short') == '1':
        return jsonify(success=True)
    return redirect(url_for('story.view', pk=story.id))


@bp.route('/<int:pk>/comments/subscribe/', methods=('POST',))
@db_session
@login_required
def comments_subscribe(pk):
    story = get_story(pk)
    story.bl.subscribe_to_comments(
        current_user,
        email=request.form.get('email') == '1',
        tracker=request.form.get('tracker') == '1',
    )

    if request.form.get('short') == '1':
        return jsonify(success=True)
    return redirect(url_for('story.view', pk=story.id))


@bp.route('/<int:pk>/localcomments/subscribe/', methods=('POST',))
@db_session
@login_required
def local_comments_subscribe(pk):
    story = get_story(pk)
    if not current_user.is_staff and not story.bl.is_contributor(current_user):
        abort(403)

    story.bl.subscribe_to_local_comments(
        current_user,
        email=request.form.get('email') == '1',
        tracker=request.form.get('tracker') == '1',
    )

    if request.form.get('short') == '1':
        return jsonify(success=True)
    return redirect(url_for('story_local_comment.view', story_id=story.id))


# this is for ajax links


@bp.route('/<int:pk>/approve/', methods=('POST',))
@db_session
@login_required
def approve(pk):
    if not current_user.is_staff:
        abort(403)  # TODO: refactor exceptions and move to bl
    story = Story.get(id=pk)
    if not story:
        abort(404)
    story.bl.approve(current_user, not story.approved)
    if g.is_ajax:
        return jsonify({'success': True, 'story_id': story.id, 'approved': story.approved})
    return redirect(url_for('story.view', pk=story.id))


@bp.route('/<int:pk>/pin/', methods=('POST',))
@db_session
@login_required
def pin(pk):
    if not current_user.is_staff:
        abort(403)  # TODO: refactor exceptions and move to bl
    story = Story.get(id=pk)
    if not story:
        abort(404)
    story.pinned = not story.pinned

    url = request.headers.get('Referer') or url_for('story.view', pk=story.id)
    if g.is_ajax:
        return jsonify({'page_content': {'redirect': url}})
    return redirect(url)


@bp.route('/<int:pk>/publish/', methods=('POST',))
@db_session
@login_required
def publish(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)

    if not current_user.is_staff and not story.bl.publishable_by(current_user):
        abort(403)

    modal = None

    data = {
        'story': story,
        'need_words': current_app.config['PUBLISH_SIZE_LIMIT'],
        'unpublished_chapters_count': Chapter.select(lambda x: x.story == story and x.draft).count(),
    }

    if story.publishing_blocked_until and story.publishing_blocked_until > datetime.utcnow():
        data['page_title'] = 'Неудачная попытка публикации'
        modal = render_template('includes/ajax/story_ajax_publish_blocked.html', **data)

    elif not story.bl.publish(current_user, story.draft):  # draft == not published
        data['page_title'] = 'Неудачная попытка публикации'
        modal = render_template('includes/ajax/story_ajax_publish_warning.html', **data)

    elif not story.draft:
        if story.approved:
            data['page_title'] = 'Рассказ опубликован'
            modal = render_template('includes/ajax/story_ajax_publish_approved.html', **data)
        else:
            data['page_title'] = 'Рассказ отправлен на модерацию'
            modal = render_template('includes/ajax/story_ajax_publish_unapproved.html', **data)

    if g.is_ajax:
        return jsonify({'success': True, 'story_id': story.id, 'published': not story.draft, 'modal': modal})
    return redirect(url_for('story.view', pk=story.id))  # TODO: add warning here too




@bp.route('/<int:pk>/favorite/<action>/', methods=('POST',))
@db_session
@login_required
def favorite(pk, action):
    if action not in ('add', 'delete'):
        abort(404)

    f = Favorites.select(lambda x: x.author == current_user and x.story.id == pk).for_update().first()
    if f and action == 'delete':
        f.delete()  # без проверки доступа
        f = None
    elif action == 'add':
        story = get_story(pk)  # проверка доступа
        f = Favorites(author=current_user, story=story)
    if g.is_ajax:
        return jsonify({
            'success': True,
            'story_id': pk,
            'favorited': f is not None,
            'change_url': url_for('story.favorite', pk=pk, action='delete' if f else 'add'),
        })
    return redirect(url_for('story.view', pk=pk))


@bp.route('/<int:pk>/bookmark/<action>/', methods=('POST',))
@db_session
@login_required
def bookmark(pk, action):
    if action not in ('add', 'delete'):
        abort(404)

    b = Bookmark.select(lambda x: x.author == current_user and x.story.id == pk).for_update().first()
    if b and action == 'delete':
        b.delete()  # без проверки доступа
        b = None
    elif action == 'add':
        story = get_story(pk)  # проверка доступа
        b = Bookmark(author=current_user, story=story)
    if g.is_ajax:
        return jsonify({
            'success': True,
            'story_id': pk,
            'bookmarked': b is not None,
            'change_url': url_for('story.bookmark', pk=pk, action='delete' if b else 'add'),
        })
    return redirect(url_for('story.view', pk=pk))


@bp.route('/<int:pk>/vote/', methods=('POST',))
@db_session
@login_required
def vote(pk):
    story = get_story(pk, for_update=True)

    try:
        value = int(request.form.get('vote_value') or '')
        vote_obj = story.bl.vote(current_user, value, ip=request.remote_addr)
    except ValueError as exc:  # TODO: refactor exceptions
        if request.form.get('vote_ajax') == '1':
            return jsonify({'error': str(exc), 'success': False, 'story_id': story.id}), 403
        abort(403)

    if request.form.get('vote_ajax') == '1':
        return jsonify({
            'success': True,
            'story_id': story.id,
            'value': value,
            'vote_view_html': current_app.story_voting.vote_view_html(story, user=current_user, full=True),
            'vote_area_1_html': current_app.story_voting.vote_area_1_html(story, user=current_user, user_vote=vote_obj),
            'vote_area_2_html': current_app.story_voting.vote_area_2_html(story, user=current_user, user_vote=vote_obj),
        })
    return redirect(url_for('story.view', pk=story.id))


@bp.route('/<int:pk>/editlog/')
@db_session
def edit_log(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.bl.can_view_editlog(current_user):
        abort(403)

    edit_log_items = story.edit_log.select().order_by(StoryLog.created_at.desc()).prefetch(StoryLog.user)

    data = dict(
        edit_log=edit_log_items,
        edit_log_users=load_users_for_editlog(edit_log_items),
        page_title='История редактирования рассказа «{}»'.format(story.title),
        story=story,
    )
    return render_template('story_edit_log.html', **data)


@bp.route('/<int:pk>/favorites/')
@db_session
def favorites(pk):
    story = get_story(pk)

    favorites_list = Favorites.select(lambda x: x.story == story).prefetch(Favorites.author)
    favorites_list = list(favorites_list.order_by(Favorites.date))

    return render_template(
        'story_favorites.html',
        story=story,
        favorites=favorites_list,
        favorites_count=len(favorites_list),
        page_title='«{}» в избранном'.format(story.title),
    )


@bp.route('/add/', methods=('GET', 'POST'))
@db_session
@login_required
def add():
    rating = Rating.select().order_by(Rating.id.desc()).first()
    form = StoryForm(data={'status': 0, 'original': 1, 'rating': rating.id if rating else 1})

    ctx = {
        'page_title': gettext('New story'),
        'form': form,
        'story_add': True,
        'saved': False,
        'not_saved': False,
    }

    if form.validate_on_submit():
        formdata = dict(form.data)
        if formdata['status'] == 0:
            formdata['status'] = 'unfinished'
        elif formdata['status'] == 1:
            formdata['status'] = 'finished'
        elif formdata['status'] == 2:
            formdata['status'] = 'freezed'

        try:
            story = Story.bl.create([current_user], formdata)
        except ValidationError as exc:
            form.set_errors(exc.errors)
            ctx['not_saved'] = True
        else:
            return redirect(url_for('story.edit_chapters', pk=story.id))

    return render_template('story_add.html', **ctx)


@bp.route('/<int:pk>/edit/', methods=('GET', 'POST'))
@db_session
@login_required
def edit(pk):
    if request.method == 'POST':
        story = Story.get_for_update(id=pk)
    else:
        story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.bl.editable_by(current_user):
        abort(403)

    story_data = {
        'tags': [x.tag.name for x in story.bl.get_tags_list()],
        'characters': [x.id for x in story.characters],
        'rating': story.rating.id,
        'original_url': story.original_url,
        'original_title': story.original_title,
        'original_author': story.original_author,
    }
    for key in ('title', 'summary', 'notes', 'original'):
        story_data[key] = getattr(story, key)

    if story.finished:
        story_data['status'] = 1
    elif story.freezed:
        story_data['status'] = 2
    else:
        story_data['status'] = 0

    form = StoryForm(data=story_data)

    ctx = {
        'saved': False,
        'not_saved': False,
        'story': story,
        'page_title': 'Редактирование «{}»'.format(story.title),
        'form': form,
        'story_tab': 'general',
    }

    if request.method == 'POST':
        if form.validate_on_submit():
            formdata = dict(form.data)
            if formdata['status'] == 0:
                formdata['status'] = 'unfinished'
            elif formdata['status'] == 1:
                formdata['status'] = 'finished'
            elif formdata['status'] == 2:
                formdata['status'] = 'freezed'

            minor = formdata.pop('minor', False)

            try:
                story = story.bl.update(current_user, formdata, minor=minor)
            except ValidationError as exc:
                form.set_errors(exc.errors)
                ctx['not_saved'] = True
            else:
                ctx['saved'] = True
                # Заголовок могли изменить, обновляем
                ctx['page_title'] = 'Редактирование «{}»'.format(story.title)
                # Приводим теги к нормализованному виду
                form.tags.data = [x.tag.name for x in story.bl.get_tags_list()]

    return render_template('story_edit_general.html', **ctx)


@bp.route('/<int:pk>/edit/chapters/', methods=('GET', 'POST'))
@db_session
@login_required
def edit_chapters(pk):
    if request.method == 'POST':
        story = Story.get_for_update(id=pk)
    else:
        story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.bl.editable_by(current_user):
        abort(403)

    ctx = {
        'story': story,
        'page_title': 'Редактирование глав «{}»'.format(story.title),
        'story_tab': 'chapters',
        'chapters': list(story.chapters.select().order_by(Chapter.order, Chapter.id)),
    }

    return render_template('story_edit_chapters.html', **ctx)


@bp.route('/<int:pk>/edit/contributors/', methods=('GET', 'POST'))
@db_session
@login_required
def edit_contributors(pk):
    if request.method == 'POST':
        story = Story.get_for_update(id=pk)
    else:
        story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.bl.can_edit_contributors(current_user):
        abort(403)

    ctx = {
        'story': story,
        'page_title': 'Редактирование авторов «{}»'.format(story.title),
        'story_tab': 'contributors',
        'contr_saved': False,
        'contr_error': None,
    }

    if request.method == 'POST':
        error = None
        access = {}
        for k, v in request.form.items():
            if not k.startswith('access_'):
                continue
            k = k[7:]

            if k == 'new' and request.form.get('access_new_user'):
                acc_user = Author.get(username=request.form['access_new_user'])
                if not acc_user:
                    error = 'Пользователь с ником {} не найден'.format(request.form.get('access_new_user') or 'N/A')
                    break
                visible = request.form.get('visible_new') == '1'
            elif k.isdigit():
                acc_user = Author.get(id=int(k))
                if not acc_user:
                    error = 'Пользователь с id {} не найден'.format(k)
                    break
                visible = request.form.get('visible_' + k) == '1'
            else:
                continue

            if not current_user.is_staff and acc_user.id == current_user.id:
                continue

            if not v:
                access[acc_user.id] = None
            elif v == 'beta':
                access[acc_user.id] = {'is_editor': False, 'is_author': False, 'visible': visible}
            elif v == 'editor':
                access[acc_user.id] = {'is_editor': True, 'is_author': False, 'visible': visible}
            elif v == 'author':
                access[acc_user.id] = {'is_editor': True, 'is_author': True, 'visible': visible}
            elif v == 'author_readonly':
                if current_user.is_staff:
                    access[acc_user.id] = {'is_editor': False, 'is_author': True, 'visible': visible}
            else:
                error = 'Некорректное значение доступа {}'.format(v)
                break

        if error:
            ctx['contr_error'] = error
            if g.is_ajax:
                page_title = 'Ошибка редактирования доступа'
                html = render_template('includes/ajax/story_edit_contributors_error.html', page_title=page_title, contr_error=error)
                return jsonify({'page_content': {'modal': html, 'title': page_title}})

        else:
            story.bl.edit_contributors(current_user, access)
            ctx['contr_saved'] = True

        if request.args.get('short') == '1':
            html = render_template('includes/story_edit_contributors_form.html', **ctx)
            return jsonify({'success': True, 'form': html})

    return render_template('story_edit_contributors.html', **ctx)


@bp.route('/<int:pk>/edit/staff/', methods=('GET', 'POST'))
@db_session
@login_required
def edit_staff(pk):
    if request.method == 'POST':
        story = Story.get_for_update(id=pk)
    else:
        story = Story.get(id=pk)
    if not story:
        abort(404)
    if not current_user.is_staff or not story.bl.editable_by(current_user):
        abort(403)

    ctx = {
        'story': story,
        'page_title': 'Администрирование рассказа «{}»'.format(story.title),
        'story_tab': 'staff',
        'staff_saved': False,
    }

    if request.method == 'POST':
        # TODO: bl
        story.robots_noindex = request.form.get('robots_noindex') == '1'
        if request.form.get('comments_mode') in {'', 'on', 'off', 'pub', 'nodraft'}:
            story.comments_mode = request.form.get('comments_mode')
        if request.form.get('direct_access') in {'', 'all', 'allguest', 'none', 'nodraft', 'anodraft'}:
            story.direct_access = request.form.get('direct_access')
        ctx['staff_saved'] = True

    return render_template('story_edit_staff.html', **ctx)


@bp.route('/<int:pk>/delete/', methods=('GET', 'POST'))
@db_session
@login_required
def delete(pk):
    story = Story.get(id=pk)
    if not story:
        abort(404)
    if not story.bl.deletable_by(current_user):
        abort(403)

    if request.method == 'POST' and (not story.first_published_at or request.form.get('agree') == '1'):
        story.bl.delete(user=current_user)
        return redirect(url_for('index.index'))

    page_title = 'Подтверждение удаления рассказа'
    data = {
        'page_title': page_title,
        'story': story,
    }

    return render_template('story_confirm_delete.html', **data)


@bp.route('/<int:story_id>/download/<filename>', methods=('GET',))
@db_session
def download(story_id, filename):
    if '.' not in filename:
        abort(404)
    full_filename = filename
    filename, extension = full_filename.split('.', 1)

    from ..downloads import get_format

    debug = current_app.config['DEBUG'] and request.args.get('debug')

    story = get_story(pk=story_id)
    if not story.published_chapters_count:
        abort(404)
    fmt = get_format(extension)
    if fmt is None:
        abort(404)

    if full_filename != fmt.filename(story):
        return redirect(fmt.url(story))
    filepath = 'stories/%s/%s.%s' % (story_id, filename, extension)

    storage_path: Path = current_app.config['MEDIA_ROOT'] / filepath

    if (
        not storage_path.exists() or
        datetime.fromtimestamp(storage_path.stat().st_mtime) < story.updated or
        debug
    ):
        data = fmt.render(
            story=story,
            debug=debug,
        )

        if not debug:
            if storage_path.exists():
                storage_path.unlink()
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            storage_path.write_bytes(data)

    # TODO: delete file if story was deleted
    if not debug:
        if current_app.config.get('ACCEL_REDIRECT_HEADER'):
            response = Response(b'', content_type=fmt.content_type)
            response.headers[current_app.config['ACCEL_REDIRECT_HEADER']] = url_for(
                'media', filename='stories/{}/{}'.format(story.id, full_filename)
            )
        else:
            response = send_file(storage_path.resolve())
            response.headers['Content-Type'] = fmt.content_type

        response.headers['Content-Disposition'] = 'attachment'

    else:
        response = Response(data, content_type=fmt.debug_content_type)

    return response


@bp.route('/<int:story_id>_dump.jsonl', methods=('GET',))
@db_session
def download_json(story_id):
    from mini_fiction.ponydump import JSONEncoder

    story = get_story(story_id)

    je = JSONEncoder(ensure_ascii=False, sort_keys=True)
    result = StringIO()

    for x in story.bl.dump_only_public(
        with_chapters=True,
        with_favorites=False,
        with_comments=False
    ):
        result.write(je.encode(x) + '\n')

    response = Response(result.getvalue(), mimetype='application/json-l')
    response.headers['X-Robots-Tag'] = 'noindex'
    return response


@bp.route('/<int:story_id>_full_dump.jsonl', methods=('GET',))
@db_session
def download_json_full(story_id):
    from mini_fiction.ponydump import JSONEncoder

    if not current_user.is_superuser:
        abort(403)

    story = get_story(story_id)

    je = JSONEncoder(ensure_ascii=False, sort_keys=True)
    result = StringIO()

    for x in story.bl.dump_full(dump_collections=False):
        result.write(je.encode(x) + '\n')

    response = Response(result.getvalue(), mimetype='application/json-l')
    response.headers['X-Robots-Tag'] = 'noindex'
    return response
