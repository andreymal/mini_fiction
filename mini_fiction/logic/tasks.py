from typing import Literal

from flask import current_app, g

RegisteredTask = Literal[
    "sendmail",
    "zip_dump",
    "sitemap_ping_story",
    "sphinx_update_story",
    "sphinx_update_chapter",
    "sphinx_update_comments_count",
    "sphinx_delete_story",
    "sphinx_delete_chapter",
    "notify_abuse_report",
    "notify_story_pubrequest",
    "notify_story_publish_noappr",
    "notify_story_delete",
    "notify_story_publish_draft",
    "notify_author_story",
    "notify_story_chapters",
    "notify_story_comment",
    "notify_story_lcomment",
    "notify_news_comment",
]


# SAFETY:
#  Registry filled in mini_fiction.tasks
#  Deliberately allow arbitrary arguments for celery tasks
def schedule_task(task: RegisteredTask, *args, **kwargs) -> None:  # type: ignore
    function = current_app.tasks[task].delay  # type: ignore
    if not hasattr(g, "after_request_callbacks"):
        g.after_request_callbacks = []
    g.after_request_callbacks.append((function, args, kwargs))
