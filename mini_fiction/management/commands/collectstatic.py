#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil

from flask import current_app


def copytree_exist(src, dest, verbose=True):
    for curdir, _, filenames in os.walk(src):
        assert curdir.startswith(src)
        curpath = curdir[len(src) + 1:]

        if not os.path.isdir(os.path.join(dest, curpath)):
            os.makedirs(os.path.join(dest, curpath))

        for filename in filenames:
            filedest = os.path.join(dest, curpath, filename)
            if verbose:
                print(os.path.join(curpath, filename), '=>', filedest)
            shutil.copy(os.path.join(src, curpath, filename), filedest)


def collectstatic():
    modulestatic = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname((__file__)))), 'static')
    assert os.path.isdir(modulestatic)
    print('Module static folder: {}'.format(modulestatic))
    projectstatic = os.path.abspath(current_app.config['STATIC_ROOT'])
    if modulestatic == projectstatic:
        print('Project static folder is the same.')
        return
    print('Project static folder: {}'.format(projectstatic))
    copytree_exist(modulestatic, projectstatic, verbose=True)
