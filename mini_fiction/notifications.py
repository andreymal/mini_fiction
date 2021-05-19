from enum import Enum, auto


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
