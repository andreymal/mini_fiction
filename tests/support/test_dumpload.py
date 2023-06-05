#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name,unused-variable

import os
import json
import zipfile
from pathlib import Path

from mini_fiction import models, dumpload
from mini_fiction.database import db


def test_zip_dump_complex(app, factories):
    zip_path = os.path.join(app.config['TESTING_DIRECTORY'], 'dump.zip')
    assert not os.path.isfile(zip_path)  # prepare

    # Этот пользователь не должен попасть в дамп
    author = factories.AuthorFactory()
    author.bl.set_password('123456')

    # Установим системному пользователю e-mail и пароль, чтобы проверить,
    # что они не попадут в дамп
    system = models.Author.get(id=-1)
    system.email = 'test@example.com'
    system.bl.set_password('123456')

    db.commit()

    try:
        dumpload.zip_dump(Path(zip_path))

        assert os.path.isfile(zip_path)

        author_dump = None
        namelist = None
        with zipfile.ZipFile(zip_path, 'r') as z:
            namelist = z.namelist()
            with z.open('dump/author_dump.jsonl', 'r') as fp:
                author_dump = fp.read().decode('utf-8')

        assert set(namelist) & {
            'dump/author_dump.jsonl',
            'dump/category_dump.jsonl',
            'dump/charactergroup_dump.jsonl',
            'dump/character_dump.jsonl',
            'dump/classifier_dump.jsonl',
            'dump/htmlblock_dump.jsonl',
            'dump/logopic_dump.jsonl',
            'dump/rating_dump.jsonl',
            'dump/staticpage_dump.jsonl',
        }

        # Проверяем, что пользователь в дампе всего один
        lines = [x for x in author_dump.split('\n') if x]
        assert len(lines) == 1

        author = json.loads(lines[0])
        assert author['_entity'] == 'author'

        # Проверяем, что это системный пользователь
        assert author['id'] == -1
        assert author['username'] == 'System'

        # Проверяем, что никакой лишней инфы не попало
        assert not author.get('email')
        assert not author.get('password')

        # TODO: проверить всё остальное

    finally:
        if os.path.isfile(zip_path):
            os.remove(zip_path)
