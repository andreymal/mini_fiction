from dataclasses import dataclass
from itertools import chain, groupby
from typing import List, Tuple

from mini_fiction.models import Story, StoryTag, Tag, TagCategory


@dataclass
class PreparedTags:
    primary: List[Tag]
    secondary: List[Tag]
    extreme: List[Tag]
    spoiler: List[Tag]


def _group_key(tag: Tag) -> TagCategory:
    return tag.category


def _extract_spoilers(tags: List[Tag]) -> Tuple[List[Tag], List[Tag]]:
    groups = [
        list(tag_group) for _, tag_group in groupby(tags, key=lambda t: t.is_spoiler)
    ]
    if len(groups) == 1:
        return groups[0], []
    return groups[0], groups[1]


def _group_tags(tags: List[Tag]) -> Tuple[List[Tag], List[Tag]]:
    grouped = [list(tag_group) for _, tag_group in groupby(tags, key=_group_key)]
    return (
        list(chain.from_iterable(group[:1] for group in grouped[:5])),
        list(
            chain(
                chain.from_iterable(group[1:] for group in grouped[:5]),
                chain.from_iterable(grouped[5:]),
            )
        ),
    )


def _get_prepared_tags(story_tags: List[StoryTag]) -> PreparedTags:
    sorted_tags: List[Tag] = sorted((st.tag for st in story_tags), key=_group_key)
    main_tags, spoiler = _extract_spoilers(sorted_tags)
    extreme = [t for t in sorted_tags if t.is_extreme_tag]

    if len(main_tags) <= 5:
        secondary: List[Tag]
        primary, secondary = main_tags, []
    else:
        primary, secondary = _group_tags(main_tags)

    return PreparedTags(
        primary=primary,
        secondary=secondary,
        extreme=extreme,
        spoiler=spoiler,
    )


def get_prepared_tags(story: Story) -> PreparedTags:
    return _get_prepared_tags(story.tags)
