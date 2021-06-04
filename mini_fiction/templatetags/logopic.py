from mini_fiction.templatetags import registry
from mini_fiction.logic import logopics


@registry.simple_tag()
def get_current_logopic():
    return logopics.get_current()

