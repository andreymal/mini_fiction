from collections import defaultdict
from dataclasses import dataclass
from itertools import chain, islice
from operator import attrgetter
from typing import List, Tuple

from mini_fiction.models import Story, StoryTag, Tag, TagCategory

MAX_TAGS = 5


@dataclass
class PreparedTags:
    primary: List[Tag]
    secondary: List[Tag]
    extreme: List[Tag]
    spoiler: List[Tag]


def _group_key(tag: Tag) -> TagCategory:
    return tag.category


def _group_spoiler(tag: Tag) -> bool:
    return tag.is_spoiler


def _extract_spoilers(tags: List[Tag]) -> Tuple[List[Tag], List[Tag]]:
    result = defaultdict(list)
    for tag in tags:
        result[tag.is_spoiler].append(tag)
    return result.get(False, []), result.get(True, [])


def _group_tags(tags: List[Tag]) -> Tuple[List[Tag], List[Tag]]:
    grouped = defaultdict(list)
    for tag in tags:
        grouped[tag.category].append(tag)

    primary: List[Tag] = []
    for tag_group in islice(grouped.values(), 0, MAX_TAGS):
        primary.append(tag_group.pop(0))

    secondary = list(chain.from_iterable(grouped.values()))

    return primary, secondary


def _get_prepared_tags(story_tags: List[StoryTag]) -> PreparedTags:
    sorted_tags: List[Tag] = sorted(
        (st.tag for st in story_tags), key=attrgetter("category", "iname")
    )
    main_tags, spoiler = _extract_spoilers(sorted_tags)
    extreme = [t for t in sorted_tags if t.is_extreme_tag]

    if len(main_tags) <= MAX_TAGS:
        return PreparedTags(
            primary=main_tags,
            secondary=[],
            extreme=extreme,
            spoiler=spoiler,
        )
    primary, secondary = _group_tags(main_tags)
    return PreparedTags(
        primary=primary,
        secondary=secondary,
        extreme=extreme,
        spoiler=spoiler,
    )


def get_prepared_tags(story: Story) -> PreparedTags:
    return _get_prepared_tags(story.tags)
