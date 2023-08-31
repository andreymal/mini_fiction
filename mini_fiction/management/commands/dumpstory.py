from pathlib import Path
from typing import Tuple

import click
from pony.orm import db_session

from mini_fiction.management.manager import cli
from mini_fiction.models import Story


@cli.command(short_help="Makes a full JSON dump of specified stories.")
@click.argument("story_ids", nargs=-1, type=int)
@click.option("-o", "--output", required=True, help="Output directory.")
@click.option(
    "-c",
    "--compression",
    "gzip_compression",
    type=click.IntRange(0, 9),
    default=0,
    help="Use gzip compression for files.",
)
@click.option("-v", "--verbose", "verbosity", count=True, help="Verbose output.")
def dumpstory(
    story_ids: Tuple[int],
    output: str,
    gzip_compression: int = 0,
    verbosity: int = 0,
) -> None:
    notfound_count = 0

    output_path = Path(output).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    for story_id in story_ids:
        if verbosity > 0:
            print(f"Dumping story {story_id}...", end=" ", flush=True)

        with db_session:
            story = Story.get(id=story_id)
            if story is None:
                print(f"WARNING: story {story_id} not found")
                notfound_count += 1
                continue

            story_dump_path = output_path / f"{story_id}_full_dump.jsonl"
            if gzip_compression:
                story_dump_path = story_dump_path.with_suffix(story_dump_path.suffix + ".gz")

            story.bl.dump_to_file_full(story_dump_path, gzip_compression)

        if verbosity > 0:
            print("Done.")

    if notfound_count > 0:
        print(f"{notfound_count} stories not found")
