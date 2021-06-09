from pathlib import Path
from typing import Type

import click
from flask import current_app
from pony import orm

from mini_fiction.logic.image import save_image, LogopicBundle, ImageBundle, CharacterBundle, AvatarBundle
from mini_fiction.management.manager import cli
from mini_fiction.models import Logopic, Character, Author


def _process_image(model, bundle_kind: Type[ImageBundle], debug: bool = False) -> None:
    media_root: Path = current_app.config["MEDIA_ROOT"]
    if not model.picture:
        print(f'There are no original picture for {model}, probably got consistency error')
        return

    raw_data = (media_root / model.picture).read_bytes()
    bundle = save_image(bundle=bundle_kind, raw_data=raw_data)
    model.image = bundle
    model.flush()
    if debug:
        print(bundle)


def _process_avatar(author: Author, debug: bool = False) -> None:
    media_root: Path = current_app.config["MEDIA_ROOT"]

    if author.avatar_large:
        raw_data = (media_root / author.avatar_large).read_bytes()
        bundle = save_image(bundle=AvatarBundle, raw_data=raw_data)
        author.image = bundle
        if debug:
            print(bundle)
    else:
        del author.image
    author.flush()


@cli.command(short_help='Converts old images', help='Convert each image to webp/jpg and fills metadata in new format')
@click.option("-v", "--verbose", "verbosity", count=True, help='Verbosity: -v prints debug logs')
def convertimages(verbosity=0):
    orm.sql_debug(False)
    debug = verbosity > 0

    with orm.db_session:
        for logopic in Logopic.select():
            _process_image(logopic, LogopicBundle, debug)
            print(f'Processed logopic {logopic.id}')

        for character in Character.select():
            _process_image(character, CharacterBundle, debug)
            print(f'Processed character {character.id}')

        for author in Author.select():
            _process_avatar(author, debug)
            print(f'Processed author {author.id}')
