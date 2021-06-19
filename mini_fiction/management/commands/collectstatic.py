import os
import shutil
from hashlib import sha256

import click
from flask import current_app

from mini_fiction.management.manager import cli


def collect_files(src, only=None, ignore=None, follow_symlinks=False):
    only = frozenset(only or ())
    ignore = frozenset(ignore or ())
    result = []

    queue = os.listdir(src)
    queue.sort(reverse=True)
    while queue:
        path = queue.pop()
        abspath = os.path.join(src, path)

        if (not follow_symlinks and os.path.islink(abspath)) or os.path.isfile(abspath):
            if only and path not in only:
                continue
            if path not in ignore:
                result.append(path)
            continue

        assert os.path.isdir(abspath)

        if path not in ignore and os.path.join(path, '') not in ignore:
            q = [os.path.join(path, x) for x in os.listdir(abspath)]
            q.sort(reverse=True)
            queue.extend(q)

    return result


def copyfile(source: str, destination: str, follow_symlinks=False, verbose=True):
    global_hash = sha256()

    if verbose:
        print(destination, end='', flush=True)

    dstdir = os.path.dirname(destination)
    if not os.path.isdir(dstdir):
        os.makedirs(dstdir)  # TODO: что-то сделать с правами

    if not follow_symlinks and os.path.islink(source):
        changed = False
        if not os.path.islink(destination) or os.readlink(source) != os.readlink(destination):
            if os.path.exists(destination):
                os.remove(destination)
            os.symlink(os.readlink(source), destination)
            changed = True
        if verbose:
            print(' (symlink)', flush=True)
        return changed

    old_hash = None
    if os.path.isfile(destination):
        old_hash_obj = sha256()
        with open(destination, 'rb') as fp:
            while True:
                chunk = fp.read(16384)
                if not chunk:
                    break
                old_hash_obj.update(chunk)
        old_hash = old_hash_obj.hexdigest()
        del old_hash_obj

    new_hash_obj = sha256()
    with open(source, 'rb') as fp:
        while True:
            chunk = fp.read(16384)
            if not chunk:
                break
            new_hash_obj.update(chunk)
            global_hash.update(chunk)
    new_hash = new_hash_obj.hexdigest()
    del new_hash_obj

    if old_hash != new_hash:
        shutil.copy2(source, destination)
        if verbose:
            print(' (updated)', flush=True)
        return True

    if verbose:
        print(' (not changed)', flush=True)
    return False


@cli.command(
    short_help='Copies static files.',
    help='Copies static files to DESTINATION directory (STATIC_ROOT by default).'
)
@click.option('-v/-V', '--verbose/--no-verbose', default=True)
@click.argument('destination', nargs=1, required=False)
def collectstatic(verbose, destination):
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

    copy_static_directory(
        source=modulestatic,
        destination=projectstatic,
        verbose=verbose,
        follow_symlinks=True,
    )


def copy_static_directory(
    *,
    source: str,
    destination: str,
    verbose=True,
    only=None,
    ignore=None,
    follow_symlinks=False
) -> None:
    modulestatic = source
    projectstatic = destination

    if not os.path.isdir(projectstatic):
        os.makedirs(projectstatic)
        shutil.copystat(modulestatic, projectstatic)

    if verbose:
        print('Collect files list...', end=' ', flush=True)
    srcfiles = collect_files(modulestatic, only=only, ignore=ignore, follow_symlinks=follow_symlinks)
    if verbose:
        print('found {} files.'.format(len(srcfiles)), flush=True)

    changed = [
        copyfile(
            source=os.path.join(modulestatic, path),
            destination=os.path.join(projectstatic, path),
            verbose=verbose,
            follow_symlinks=follow_symlinks
        )
        for path in srcfiles
    ]

    if verbose:
        print('{} files updated.'.format(changed.count(True)))
