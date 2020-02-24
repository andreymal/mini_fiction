#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from flask import current_app

from mini_fiction.management.manager import cli


@cli.command(help='Prints config for Sphinx/Manticore search daemon')
def sphinxconf():
    cfg = current_app.config['SPHINX_CONFIG']
    cfg_index = current_app.config['SPHINX_INDEX_OPTIONS']

    root = os.path.abspath(current_app.config['SPHINX_ROOT'])
    if not os.path.isdir(root):
        raise IOError('Missing search root directory: {!r}'.format(root))
    root_prefix = os.path.join(root, '')
    assert root_prefix.endswith(os.path.sep)

    binlog_path = os.path.join(root, 'binlog')
    stories_index_path = os.path.join(root, 'stories')
    stories_index_name = 'stories'
    chapters_index_path = os.path.join(root, 'chapters')
    chapters_index_name = 'chapters'

    for p in (binlog_path, stories_index_path, chapters_index_path):
        if p.startswith(root_prefix) and not os.path.exists(p):
            os.makedirs(p)

    wordforms_cfg = ''
    if cfg_index.get('wordforms'):
        wordforms_cfg = 'wordforms = {}'.format(os.path.abspath(
            str(cfg_index['wordforms'])
        ))

    exceptions_cfg = ''
    if cfg_index.get('exceptions'):
        exceptions_cfg = 'exceptions = {}'.format(os.path.abspath(
            str(cfg_index['exceptions'])
        ))

    ctx = {
        'sphinxroot': root,
        'binlog_path': binlog_path,

        'morphology': cfg_index['morphology'],
        'min_word_len': cfg_index['min_word_len'],
        'min_infix_len': cfg_index['min_infix_len'],
        'index_exact_words': cfg_index['index_exact_words'],
        'wordforms_cfg': wordforms_cfg,
        'exceptions_cfg': exceptions_cfg,

        'stories_index_path': stories_index_path,
        'stories_index_name': stories_index_name,
        'stories_rt_mem_limit': cfg['stories_rt_mem_limit'],

        'chapters_index_path': chapters_index_path,
        'chapters_index_name': chapters_index_name,
        'chapters_rt_mem_limit': cfg['chapters_rt_mem_limit'],
    }

    project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    with open(os.path.join(project_root, 'sphinx.conf'), 'r', encoding='utf-8-sig') as fp:
        tmp = fp.read()
    buf = [tmp.rstrip().format(**ctx)]

    if current_app.config['SPHINX_COMMON']:
        buf.append('\n\ncommon {\n')
        for k, v in current_app.config['SPHINX_COMMON'].items():
            buf.append('    {0} = {1}\n'.format(k, str(v).format(**ctx)))
        buf.append('}\n')

    if current_app.config['SPHINX_SEARCHD']:
        buf.append('\n\nsearchd {\n')
        for k, v in current_app.config['SPHINX_SEARCHD'].items():
            buf.append('    {0} = {1}\n'.format(k, str(v).format(**ctx)))
        buf.append('}\n')

    if current_app.config['SPHINX_CUSTOM']:
        buf.append('\n')
        buf.append(current_app.config['SPHINX_CUSTOM'].format(**ctx))

    print(''.join(buf).rstrip())
