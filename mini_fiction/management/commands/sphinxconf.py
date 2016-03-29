#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from flask import current_app


def sphinxconf():
    sphinxroot = os.path.abspath(current_app.config['SPHINX_ROOT'])

    project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    with open(os.path.join(project_root, 'sphinx.conf'), 'r', encoding='utf-8-sig') as fp:
        tmp = fp.read()
    buf = [tmp.rstrip().format(sphinxroot=sphinxroot)]

    if current_app.config['SPHINX_SEARCHD']:
        buf.append('\n\nsearchd {\n')
        for k, v in current_app.config['SPHINX_SEARCHD'].items():
            buf.append('    {0} = {1}\n'.format(k, str(v).format(sphinxroot=sphinxroot)))
        buf.append('}\n')

    if current_app.config['SPHINX_CUSTOM']:
        buf.append('\n')
        buf.append(current_app.config['SPHINX_CUSTOM'].format(sphinxroot=sphinxroot))

    print(''.join(buf).rstrip())
