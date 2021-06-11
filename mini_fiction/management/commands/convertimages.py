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
    if not model.image_bundle:
        print(f'There are no image_bundle for {model}, probably got consistency error')
        return
    if not model.image:
        print(f'There are no image for {model}, probably it is not set at all')
        return

    raw_data = (media_root / model.image.original).read_bytes()
    bundle = save_image(bundle=bundle_kind, raw_data=raw_data)
    model.image = bundle
    model.flush()
    if debug:
        print(bundle)


@cli.command(short_help='Converts old images', help='Convert each image to appropriate format and fills metadata')
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
            _process_image(author, AvatarBundle, debug)
            print(f'Processed author {author.id}')
