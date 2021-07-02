from mini_fiction.logic.tags import get_prepared_tags


def enrich_story(story):
    prepared_tags = get_prepared_tags(story)

    setattr(story, 'prepared_tags', prepared_tags)


def enrich_stories(stories):
    for story in stories:
        enrich_story(story)
