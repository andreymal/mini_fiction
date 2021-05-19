import json
from enum import Enum, auto
from typing import Union, Optional, Literal, TypedDict, Dict

from flask import current_app

from mini_fiction.models import (
    Author,
    Chapter,
    Story,
    StoryComment,
    StoryLocalComment,
    Notification,
    NewsComment
)

Comments = Union[StoryComment, StoryLocalComment, NewsComment]


class Extras(TypedDict):
    is_editor: bool
    is_author: bool
    is_staff: bool
    unknown: bool


MaybeExtras = Optional[Extras]


class AutoName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()


class NotifyKind(AutoName):
    """Типы уведомлений"""

    AUTHOR_STORY = auto()
    """Новый рассказ от интересующего автора"""
    NEWS_REPLY = auto()
    """Ответ на комментарий к новости"""
    NEWS_COMMENT = auto()
    """Просто новый комментарий"""
    STORY_CHAPTER = auto()
    """Новая глава в рассказе"""
    STORY_REPLY = auto()
    """Ответ на комментарий к рассказу"""
    STORY_COMMENT = auto()
    """Не ответ, просто новый комментарий"""
    STORY_LREPLY = auto()
    """Ответ на комментарий в редакторской"""
    STORY_LCOMMENT = auto()
    """Новый комментарий в редакторской"""
    STORY_DRAFT = auto()
    """Модератор отклонил рассказ"""
    STORY_PUBLISH = auto()
    """Модератор опубликовал рассказ"""


StoryNotifyKind = Literal[NotifyKind.STORY_PUBLISH, NotifyKind.STORY_DRAFT, NotifyKind.AUTHOR_STORY]

CommentNotifyKind = Literal[
    NotifyKind.NEWS_REPLY,
    NotifyKind.NEWS_COMMENT,
    NotifyKind.STORY_LREPLY,
    NotifyKind.STORY_LCOMMENT,
    NotifyKind.STORY_REPLY,
    NotifyKind.STORY_COMMENT,
]


def _notify(
    to: Author,
    typ: NotifyKind,
    target: Union[Story, Chapter, Comments],
    by: Optional[Author],
    extra: Dict[str, bool]
) -> None:
    Notification(
        user=to,
        type=typ.value,
        target_id=target.id,
        caused_by_user=by,
        extra=json.dumps(extra, ensure_ascii=False, sort_keys=True),
    )
    current_app.cache.delete(f"bell_{to.id}")
    current_app.cache.delete(f"bell_content_{to.id}")


def notify_comment(*, to: Author, kind: CommentNotifyKind, comment: Comments, by: Author, extra: MaybeExtras = None):
    _notify(to, kind, comment, by, extra or {})


def notify_chapter(*, to: Author, chapter: Chapter) -> None:
    _notify(to, NotifyKind.STORY_CHAPTER, chapter, None, {})


def notify_story(*, to: Author, kind: StoryNotifyKind, story: Story, by: Optional[Author] = None) -> None:
    _notify(to, kind, story, by, {})
