import os
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from mini_fiction import ponydump
from mini_fiction.logic.image import SavedImage

# Вообще всё будет работать и без этих exclude, но выкидывание избыточной
# информации о связях сильно уменьшает размер дампа

# TODO: wrap into dataclass
dumpdb_params = {
    'story': {'exclude': (
        'edit_log', 'story_views_set', 'votes', 'favorites', 'bookmarks',
        'comments', 'activity', 'local', 'in_series_permissions',
        'contributors', 'chapters', 'tags', 'tags_log',
    )},
    'author': {'exclude': (
        'activity', 'edit_log',
        'favorites', 'bookmarks', 'contributing', 'coauthorseries',
        'news', 'votes', 'views',
        'news_comments', 'news_comment_edits', 'news_comment_votes',
        'news_last_edited_comments', 'news_deleted_comments',
        'story_comments', 'story_comment_edits', 'story_comment_votes',
        'story_last_edited_comments', 'story_deleted_comments',
        'story_local_comments', 'story_local_comment_edits',
        'story_local_last_edited_comments', 'story_local_deleted_comments',
        'contacts', 'subscriptions', 'notifications',
        'created_notifications', 'published_stories', 'approvals',
        'registration_profiles',
        'change_email_profiles', 'password_reset_profiles',
        'abuse_reports', 'admin_log', 'tags_created', 'tags_log',
    )},
    'chapter': {'exclude': (
        'edit_log', 'chapter_views_set',
    )},
    'storycomment': {'exclude': (
        'answers', 'edits', 'votes',
    )},
    'storylocalthread': {'exclude': (
        'comments',
    )},
    'storylocalcomment': {'exclude': (
        'answers', 'edits',
    )},
    'newsitem': {'exclude': (
        'comments',
    )},
    'newscomment': {'exclude': (
        'answers', 'edits', 'votes',
    )},
    'character': {'exclude': (
        'stories',
    )},
    'tagcategory': {'exclude': (
        'tags',
    )},
    'tag': {'exclude': (
        'aliases', 'stories', 'log',
    )},
    'rating': {'exclude': (
        'stories',
    )},
    'series': {'exclude': (
        'permissions',
    )},
    'adminlogtype': {'exclude': (
        'log',
    )},
}


# В целях безопасности и защиты от дурака ВСЕ поля моделей для zip-дампа
# должны быть упомянуты в include, exclude или override (но не media)
zip_dump_params = {
    'logopic': {
        'include': (
            'id', 'image_bundle', 'visible', 'description',
            'original_link', 'original_link_label', 'created_at', 'updated_at',
        ),
        'datekey': 'updated_at',
        'media': ('image_bundle',),
    },
    'charactergroup': {
        'include': ('id', 'name', 'description'),
        'exclude': ('characters',),
    },
    'character': {
        'include': ('id', 'name', 'description', 'image_bundle', 'group'),
        'exclude': (
            'stories',
        ),
        'media': ('image_bundle',),
    },
    'tagcategory': {
        'include': ('id', 'name', 'description', 'created_at', 'updated_at'),
        'exclude': ('tags',),
    },
    'tag': {
        'include': (
            'id', 'name', 'iname', 'category', 'description',
            'is_spoiler', 'created_at', 'updated_at', 'is_alias_for',
            'is_hidden_alias', 'is_extreme_tag', 'reason_to_blacklist',
        ),
        'exclude': (
            'created_by', 'stories_count', 'published_stories_count',
            'aliases', 'stories', 'log',
        ),
    },
    'rating': {
        'include': ('id', 'name', 'description', 'nsfw'),
        'exclude': ('stories',),
    },
    'staticpage': {
        'include': ('name', 'lang', 'title', 'content', 'is_template', 'is_full_page', 'date', 'updated'),
        'datekey': 'updated',
    },
    'htmlblock': {
        'include': ('name', 'lang', 'title', 'content', 'is_template', 'cache_time', 'date', 'updated'),
        'datekey': 'updated',
    },
    'adminlogtype': {
        'include': ('id', 'model'),
        'exclude': ('log',),
    },
    'author': {
        # Дампится только один системный пользователь
        'include': (
            'bio', 'date_joined', 'first_name', 'image_bundle',
            'id', 'is_active', 'is_staff', 'is_superuser', 'last_name', 'last_visit', 'username',
            'activated_at', 'last_login', 'text_source_behaviour',
        ),
        'exclude': (
            'comment_spoiler_threshold', 'comments_maxdepth', 'detail_view', 'excluded_categories',
            'last_viewed_notification_id', 'nsfw', 'premoderation_mode', 'last_password_change',
            'silent_email', 'silent_tracker', 'comments_per_page', 'header_mode', 'extra',
            'ban_reason', 'published_stories_count', 'all_story_comments_count', 'timezone',
            'session_token',
        ),
        'override': {'email': '', 'password': ''},
        'with_collections': False,
        'media': ('image_bundle',),
    },
}


class MiniFictionDump(ponydump.PonyDump):
    def __init__(self, database=None, dict_params=None, chunk_sizes=None, default_chunk_size=250):
        if database is None:
            from mini_fiction.database import db
            database = db

        ready_dict_params = dict(dumpdb_params)
        if dict_params:
            ready_dict_params.update(dict(dict_params))

        full_chunk_sizes = {
            'chapter': 25,
            'story': 100,
        }
        if chunk_sizes:
            full_chunk_sizes.update(chunk_sizes)

        super().__init__(
            database,
            dict_params=ready_dict_params,
            chunk_sizes=full_chunk_sizes,
            default_chunk_size=default_chunk_size,
        )

        # В PonyDump._build_depmap() сортировка моделей по опциональным
        # зависимостям не определена, но вот эти небольшие перестановки
        # сильно улучшают производительность за счёт меньшего использования
        # depcache
        self.put_depmap_entity_after('series', after_entity='story')
        self.put_depmap_entity_after('coauthorsseries', after_entity='series')
        self.put_depmap_entity_after('inseriespermissions', after_entity='coauthorsseries')
        self.put_depmap_entity_after('activity', after_entity=None)  # После всех
        self.put_depmap_entity_after('storyview', after_entity=None)


def dumpdb_console(dirpath, entities_list=None, gzip_compression=0, verbosity=2):
    from mini_fiction.utils.misc import progress_drawer

    mfd = MiniFictionDump()

    ljust_cnt = max(len(x) for x in mfd.entities) + 2

    drawer = None
    current_entity = None
    for status in mfd.dump_to_directory(dirpath, entities_list, gzip_compression=gzip_compression):
        if not status['entity']:
            # Закончилось всё
            if verbosity:
                print()
            continue

        if current_entity != status['entity']:
            current_entity = status['entity']
            if verbosity == 1:
                print(current_entity, end='... ')
                sys.stdout.flush()

        if verbosity >= 2 and not drawer:
            print(current_entity.ljust(ljust_cnt), end='')
            drawer = progress_drawer(status['count'], show_count=True)
            drawer.send(None)
            drawer.send(status['current'])

        if not status['pk']:
            # Закончилась одна модель
            if verbosity >= 2:
                try:
                    drawer.send(None)
                except StopIteration:
                    pass
                drawer = None
                if verbosity:
                    print()
            elif verbosity:
                print('ok. {}'.format(status['count']))
            continue

        if verbosity >= 2:
            drawer.send(status['current'])


def loaddb_console(paths, verbosity=2, only_create=False):
    from mini_fiction.utils.misc import progress_drawer

    mfd = MiniFictionDump()

    filelist = mfd.walk_all_paths(paths)
    if not filelist:
        raise OSError('Cannot find dump files')
    ljust_cnt = max(len(path.name) for _, path in filelist) + 2

    created = 0
    updated = 0
    not_changed = 0

    drawer = None
    current_path = None
    for statuses in mfd.load_from_files(filelist=filelist, only_create=only_create):
        for status in statuses:
            if status['pk'] is None:
                continue
            if status['created']:
                created += 1
            elif status['updated']:
                updated += 1
            else:
                not_changed += 1

        status = statuses[-1]
        if not status['path']:
            # Закончилось всё
            if verbosity:
                print()
            continue

        if current_path != status['path']:
            current_path = status['path']
            if verbosity == 1:
                print(current_path.name, end='... ')
                sys.stdout.flush()

        if verbosity >= 2 and not drawer:
            print(current_path.name.ljust(ljust_cnt), end='')
            drawer = progress_drawer(status['count'] or 0, show_count=bool(status['count']))
            drawer.send(None)
            drawer.send(status['current'])

        if not status['entity']:
            # Закончился текущий файл
            if verbosity >= 2:
                try:
                    drawer.send(None)
                except StopIteration:
                    pass
                drawer = None
                print()
            elif verbosity:
                if status['count'] is not None:
                    print('ok. {}'.format(status['count'] or 0))
                else:
                    print('ok.')
            continue

        if verbosity >= 2:
            drawer.send(status['current'])

    if only_create:
        assert not updated

    if verbosity:
        if only_create:
            print('Finished. {} objects created'.format(created))
        else:
            print('Finished. {} objects created, {} updated, {} not changed'.format(created, updated, not_changed))

    depcache = mfd.get_depcache_dict()
    if depcache:
        print()
        print('WARNING: some optional relations are broken!')
        for k, rel_dicts in depcache.items():
            print('{}.{} > {}:'.format(k[0][0], k[0][1], k[1][0]))
            for obj_pk, deps in rel_dicts[0].items():
                for dep_pk in deps:
                    print('  - {} > {}'.format(
                        obj_pk[0] if len(obj_pk) == 1 else obj_pk,
                        dep_pk[0] if len(dep_pk) == 1 else dep_pk,
                    ))


def zip_dump(path: Path, params=None, keep_broken=False):
    """
    Создаёт дамп некоторых моделей сайта, безопасный для публичного
    распространения: жанры, персонажи, HTML-блоки, системная учётная запись
    (без e-mail и пароля, конечно) и т.п.
    """

    from mini_fiction import database

    if not params:
        params = zip_dump_params

    if path.exists():
        raise ValueError(f'File {path.as_posix()} already exists')

    es = ponydump.get_entities_dict(database.db)

    # Проверяем упоминания атрибутов и собираем dict_params
    dict_params = {}
    for name, e_params in params.items():
        entity = es[name]
        dict_params[name] = {'only': []}

        include = e_params.get('include') or ()
        exclude = e_params.get('exclude') or ()
        override = e_params.get('override') or {}
        media = e_params.get('media') or ()
        with_collections = e_params.get('with_collections', True)

        # Проверяем, что все атрибуты (с коллекциями или без) упомянуты
        # (media не считается, так как оно не участвует в создании дампа БД)
        missing = set()
        for attr in entity._get_attrs_(with_collections=with_collections, with_lazy=True):
            if attr.name in include:
                dict_params[name]['only'].append(attr.name)
            elif attr.name not in exclude and attr.name not in override:
                missing.add(attr.name)

        if missing:
            raise ValueError('Missing attributes for entity {}: {}'.format(name, ', '.join(sorted(missing))))

        # Проверяем, что никаких несуществующих атрибутов не упомянуто
        # (здесь with_collections=True, так можно)
        attrs = set(x.name for x in entity._get_attrs_(with_collections=True, with_lazy=True))
        extra = set()
        for attr in set(include) | set(exclude) | set(override) | set(media):
            if attr not in attrs:
                extra.add(attr)

        if extra:
            raise ValueError('Unexpected attributes for entity {}: {}'.format(name, ', '.join(sorted(extra))))

        del missing, extra

    # Всё проверено, приступаем к дампу
    mfd = MiniFictionDump(dict_params=dict_params)

    try:
        with ZipFile(path, 'w', compression=ZIP_DEFLATED) as z:  # type: ZipFile
            media_files: List[SavedImage] = []

            # Дампим БД и попутно собираем список файлов из media
            for name, e_params in params.items():
                media_files.extend(zip_dump_db_entity(z, mfd, name, e_params))

            # Дампим файлы из media
            zip_dump_media(z, media_files)

    except:
        # В случае проблем или Ctrl+C не оставляем битый файл валяться
        if not keep_broken and path.exists():
            path.unlink()
        raise


def zip_dump_db_entity(z: ZipFile, mfd: MiniFictionDump, name: str, e_params) -> List[SavedImage]:
    from pony import orm
    from flask import current_app

    include = e_params.get('include') or ()
    exclude = e_params.get('exclude') or ()
    override = e_params.get('override') or {}
    media = e_params.get('media') or ()

    date = [None]
    media_files: List[SavedImage] = []

    def sanitizer(dump):
        for obj in dump[:]:
            # Проверяем, что атрибуты в дампе те, что прописаны в params
            for k, v in obj.items():
                if k == '_entity':
                    if v != name:
                        raise ValueError(f'Unexpected entity in zip dump! Expected {name}, got {v}')
                elif k in exclude:
                    raise ValueError(f'Security problem: excluded attribute {name}.{k} is still stored in dump')
                else:
                    assert k in include or k in override

            # Перезаписываем то, что просили перезаписать
            obj.update(override.copy())

            # Убираем из дампа скрытые картинки в шапке
            if obj['_entity'] == 'logopic':
                if not obj['visible']:
                    dump.remove(obj)
                    continue

            # Убираем из дампа теги из черного списка
            if obj['_entity'] == 'tag':
                if obj['reason_to_blacklist']:
                    dump.remove(obj)
                    continue

            # Если есть поля, указывающие на файлы в media, то дампим эти файлы
            for attr in media:
                if obj.get(attr):
                    assert isinstance(obj[attr], dict)
                    media_files.append(SavedImage.parse_obj(obj[attr]))

            # Если у модели есть дата, самую позднюю будем использовать как дату файла в архиве
            # (date[0] вместо просто date для имитации nonlocal в старых питонах)
            if e_params.get('datekey') and e_params['datekey'] in obj:
                if not date[0] or obj[e_params['datekey']] > date[0]:
                    date[0] = obj[e_params['datekey']]

    # Нам нужно собрать некоторую мета-инфу, поэтому сперва пишем в буфер
    fp = BytesIO()

    # Всё дампим как обычно, кроме пользователя, его дампим только одного — системного
    if name == 'author':
        with orm.db_session:
            obj = mfd.entities['author'].get(id=current_app.config['SYSTEM_USER_ID'])
            dump = mfd.obj2json(obj, name='author')
            sanitizer([dump])
            fp.write(mfd.je.encode(dump).encode('utf-8'))
            fp.write(b'\n')

    else:
        for _ in mfd.dump_entity(name, fp, binary_mode=True, sanitizer=sanitizer):
            pass

    if not date[0] or date[0].year <= 1980:
        date[0] = datetime.utcnow()

    # Подготавливаем мета-инфу
    zipinfo = ZipInfo(
        'dump/{}_dump.jsonl'.format(name),
        date_time=date[0].timetuple()[:6],
    )
    zipinfo.compress_type = ZIP_DEFLATED

    # Теперь пишем подготовленный дамп в архив
    z.writestr(zipinfo, fp.getvalue())
    return media_files


def zip_dump_media(z: ZipFile, media_files: List[SavedImage]):
    from flask import current_app
    media_dir = current_app.config['MEDIA_ROOT']

    for image in media_files:
        # Write original
        z.write(media_dir / image.original, f'media/{image.original}', compress_type=ZIP_DEFLATED)
        # Write images from resized bundle
        for name, meta in image.resized:
            if name.startswith('x'):
                z.write(media_dir / meta.webp, f'media/{meta.webp}', compress_type=ZIP_DEFLATED)
                z.write(media_dir / meta.png, f'media/{meta.png}', compress_type=ZIP_DEFLATED)
                z.write(media_dir / meta.jpeg, f'media/{meta.jpeg}', compress_type=ZIP_DEFLATED)
