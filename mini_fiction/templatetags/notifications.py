from mini_fiction.templatetags import registry

from flask_login import current_user


@registry.simple_tag()
def get_unread_notifications_count():
    if not current_user.is_authenticated:
        return 0
    known_unread_count = current_user.bl.get_cached_unread_notifications_count()
    return known_unread_count or 0
