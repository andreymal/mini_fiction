#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from hashlib import sha256
from datetime import datetime

from flask import current_app

from mini_fiction.management.manager import manager


def collect_files(src):
    result = []

    queue = os.listdir(src)
    queue.sort(reverse=True)
    while queue:
        path = queue.pop()
        abspath = os.path.join(src, path)

        if os.path.islink(abspath) or os.path.isfile(abspath):
            result.append(path)
            continue

        assert os.path.isdir(abspath)

        q = [os.path.join(path, x) for x in os.listdir(abspath)]
        q.sort(reverse=True)
        queue.extend(q)

    return result


def copyfile(src, dst, global_hash, verbose=True):
    if verbose:
        print(dst, end='', flush=True)

    dstdir = os.path.dirname(dst)
    if not os.path.isdir(dstdir):
        os.makedirs(dstdir)  # TODO: что-то сделать с правами

    if os.path.islink(src):
        changed = False
        if not os.path.islink(dst) or os.readlink(src) != os.readlink(dst):
            os.remove(dst)
            os.symlink(os.readlink(src), dst)
            changed = True
        if verbose:
            print(' (symlink)', flush=True)
        return changed

    old_hash = None
    if os.path.isfile(dst):
        old_hash_obj = sha256()
        with open(dst, 'rb') as fp:
            while True:
                chunk = fp.read(16384)
                if not chunk:
                    break
                old_hash_obj.update(chunk)
        old_hash = old_hash_obj.hexdigest()
        del old_hash_obj

    new_hash_obj = sha256()
    with open(src, 'rb') as fp:
        while True:
            chunk = fp.read(16384)
            if not chunk:
                break
            new_hash_obj.update(chunk)
            global_hash.update(chunk)
    new_hash = new_hash_obj.hexdigest()
    del new_hash_obj

    if old_hash != new_hash:
        shutil.copy2(src, dst)
        if verbose:
            print(' (updated)', flush=True)
        return True

    if verbose:
        print(' (not changed)', flush=True)
    return False


@manager.option('-V', '--no-verbose', dest='verbose', help='Disable verbose output', action='store_false', default=True)
@manager.option('destination', metavar='path/to/static', nargs='?', help='Target directory (default: STATIC_ROOT option)')
def collectstatic(verbose=True, destination=None):
    modulestatic = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname((__file__)))), 'static')
    assert os.path.isdir(modulestatic)
    if verbose:
        print('Module static folder: {}'.format(modulestatic))

    projectstatic = os.path.abspath(destination or current_app.config['STATIC_ROOT'])
    if modulestatic == projectstatic:
        if verbose:
            print('Project static folder is the same.')
        return

    if verbose:
        print('Project static folder: {}'.format(projectstatic))

    copy_static_directory(modulestatic, projectstatic, verbose=verbose, static_version_file=current_app.config.get('STATIC_VERSION_FILE'))


def copy_static_directory(src, dst, verbose=True, static_version_file=None):
    modulestatic = src
    projectstatic = dst

    if not os.path.isdir(projectstatic):
        os.makedirs(projectstatic)
        shutil.copystat(modulestatic, projectstatic)

    if verbose:
        print('Collect files list...', end=' ', flush=True)
    srcfiles = collect_files(modulestatic)
    if verbose:
        print('found {} files.'.format(len(srcfiles)), flush=True)

    global_hash = sha256()
    changed_cnt = 0

    for path in srcfiles:
        src = os.path.join(modulestatic, path)
        dst = os.path.join(projectstatic, path)
        if copyfile(src, dst, global_hash=global_hash, verbose=verbose):
            changed_cnt += 1

    if verbose:
        print('{} files updated.'.format(changed_cnt))

    if changed_cnt > 0 and static_version_file:
        version_file_path = os.path.join(projectstatic, static_version_file)
        if not os.path.isdir(os.path.dirname(version_file_path)):
            os.makedirs(os.path.dirname(version_file_path))

        old_ver = None
        if os.path.isfile(version_file_path):
            with open(version_file_path, 'r', encoding='utf-8') as fp:
                old_ver = fp.read().strip()

        if current_app.config.get('STATIC_VERSION_TYPE') == 'date':
            new_ver = datetime.now().strftime('%Y%m%d')
            if new_ver == old_ver:
                new_ver += '.1'
        elif current_app.config.get('STATIC_VERSION_TYPE') == 'hash':
            new_ver = global_hash.hexdigest()[:8]

        if old_ver != new_ver:
            with open(version_file_path, 'w', encoding='utf-8') as fp:
                fp.write(new_ver + '\n')

    return changed_cnt
