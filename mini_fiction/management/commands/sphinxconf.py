#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from flask import current_app

from mini_fiction.management.manager import manager


@manager.command
def sphinxconf():
    ctx = {
        'sphinxroot': os.path.abspath(current_app.config['SPHINX_ROOT']),
        'stories_rt_mem_limit': current_app.config['SPHINX_CONFIG']['stories_rt_mem_limit'],
        'chapters_rt_mem_limit': current_app.config['SPHINX_CONFIG']['chapters_rt_mem_limit'],
    }

    project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    with open(os.path.join(project_root, 'sphinx.conf'), 'r', encoding='utf-8-sig') as fp:
        tmp = fp.read()
    buf = [tmp.rstrip().format(**ctx)]

    if current_app.config['SPHINX_SEARCHD']:
        buf.append('\n\nsearchd {\n')
        for k, v in current_app.config['SPHINX_SEARCHD'].items():
            buf.append('    {0} = {1}\n'.format(k, str(v).format(**ctx)))
        buf.append('}\n')

    if current_app.config['SPHINX_CUSTOM']:
        buf.append('\n')
        buf.append(current_app.config['SPHINX_CUSTOM'].format(**ctx))

    print(''.join(buf).rstrip())
