from pathlib import Path
from typing import Tuple

import click
from flask import current_app
from pony.orm import db_session

from mini_fiction.management.manager import cli
from mini_fiction.models import Author, NewsItem, StoryContributor
from mini_fiction.utils import misc


@cli.command(short_help="Deletes specified users.")
@click.argument("author_ids", nargs=-1, type=int)
@click.option("--dry-run", "dry_run", is_flag=True, help="Just print usernames.")
@click.option("--force", "force", is_flag=True, help="Disable safety checks.")
@click.option("-v", "--verbose", "verbosity", count=True, help="Verbose output.")
def deleteauthor(
    author_ids: Tuple[int],
    dry_run: bool = False,
    force: bool = False,
    verbosity: int = 0,
) -> None:
    notfound_count = 0
    skipped_count = 0

    for author_id in author_ids:
        with db_session:
            author = Author.get(id=author_id)
            if author is None:
                print(f"WARNING: user {author_id} not found")
                notfound_count += 1
                continue

            if author.id == current_app.config["SYSTEM_USER_ID"]:
                print(f"WARNING: user {author.username} (id {author_id}) is system user")
                skipped_count += 1
                continue

            if not force:
                if author.is_staff or author.is_superuser:
                    print(f"WARNING: user {author.username} (id {author_id}) is staff")
                    skipped_count += 1
                    continue

                stories_count = StoryContributor.select(lambda c: c.user.id == author_id and c.is_author).count()
                if stories_count > 0:
                    print(f"WARNING: user {author.username} (id {author_id}) is an author of {stories_count} stories")
                    skipped_count += 1
                    continue

                news_count = NewsItem.select(lambda c: c.author.id == author_id).count()
                if news_count > 0:
                    print(f"WARNING: user {author.username} (id {author_id}) is an author of {news_count} news")
                    skipped_count += 1
                    continue

            if verbosity > 0:
                print(f"Deleting user {author.username} (id {author_id})...", end=" ", flush=True)

            if not dry_run:
                author.bl.delete()
            else:
                print("(dry run)", end=" ")

            if verbosity > 0:
                print("Done.")

        misc.call_after_request_callbacks()  # Тут удалятся файлы аватарок

    if notfound_count:
        print(f"{notfound_count} users not found")
    if skipped_count:
        print(f"{skipped_count} users skipped")
