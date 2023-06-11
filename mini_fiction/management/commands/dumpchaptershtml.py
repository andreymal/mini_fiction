import sys
from pathlib import Path
from typing import Optional

import click
from pony.orm import db_session

from mini_fiction.management.manager import cli
from mini_fiction.models import Chapter


@cli.command(short_help="Dumps formatted chapter texts.")
@click.option("--from", "from_story_id", type=int, help="Start with specified story id")
@click.option("--to", "to_story_id", type=int, help="Start at specified story id")
@click.argument("output_directory")
def dumpchaptershtml(
    output_directory: str,
    from_story_id: Optional[int] = None,
    to_story_id: Optional[int] = None,
) -> None:
    output_path = Path(output_directory)
    isatty = sys.stderr.isatty()
    last_chapter_id: Optional[int] = None

    count = 0
    empty_count = 0

    while True:
        with db_session:
            qs = Chapter.select()
            if last_chapter_id is not None:
                qs = qs.filter(lambda c: c.id > last_chapter_id)
            if from_story_id is not None:
                qs = qs.filter(lambda c: c.story.id >= from_story_id)
            if to_story_id is not None:
                qs = qs.filter(lambda c: c.story.id <= to_story_id)

            qs = qs.prefetch(Chapter.notes, Chapter.text).order_by(Chapter.id)

            chapters = list(qs[:20])
            if not chapters:
                break

            for chapter in chapters:
                last_chapter_id = chapter.id

                if isatty:
                    print(f"\r\033[K{chapter.id}", end="", file=sys.stderr, flush=True)

                if not chapter.notes and not chapter.text:
                    empty_count += 1
                    continue
                count += 1

                story_id = chapter.story.id
                chapter_path = output_path / str(story_id // 1000) / str(story_id) / f"{chapter.order:03d}.html"
                chapter_path.parent.mkdir(parents=True, exist_ok=True)

                with chapter_path.open("w", encoding="utf-8") as fp:
                    if chapter.notes:
                        fp.write(chapter.notes_as_html)
                        fp.write("\n\n")
                    fp.write(chapter.text_as_html)
                    fp.write("\n")

    if isatty:
        print(f"\r\033[KDumped {count} chapters, skipped {empty_count} empty chapters.", file=sys.stderr)
