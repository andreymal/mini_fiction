from operator import attrgetter

from mini_fiction.logic.tags import get_prepared_tags


def enrich_story(story):
    prepared_tags = get_prepared_tags(story)
    prepared_characters = sorted(story.characters, key=attrgetter('id'))

    setattr(story, 'prepared_tags', prepared_tags)
    setattr(story, 'prepared_characters', prepared_characters)


def enrich_stories(stories):
    for story in stories:
        enrich_story(story)
