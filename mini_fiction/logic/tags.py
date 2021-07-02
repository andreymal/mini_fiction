from dataclasses import dataclass
from itertools import chain, groupby
from typing import List

from mini_fiction.models import Story, StoryTag, Tag, TagCategory


@dataclass
class PreparedTags:
    primary: List[Tag]
    secondary: List[Tag]
    extreme: List[Tag]


def _group_key(tag: Tag) -> TagCategory:
    return tag.category


def _get_prepared_tags(story_tags: List[StoryTag]) -> PreparedTags:
    sorted_tags: List[Tag] = sorted((st.tag for st in story_tags), key=_group_key)

    if len(sorted_tags) <= 5:
        primary = sorted_tags
        secondary = []
    else:
        grouped = [
            list(tag_group) for _, tag_group in groupby(sorted_tags, key=_group_key)
        ]
        primary = list(chain.from_iterable(group[:1] for group in grouped[:5]))
        secondary = list(
            chain(
                chain.from_iterable(group[1:] for group in grouped[:5]),
                chain.from_iterable(grouped[5:]),
            )
        )

    extreme = [t for t in sorted_tags if t.is_extreme_tag]

    return PreparedTags(primary=primary, secondary=secondary, extreme=extreme)


def get_prepared_tags(story: Story) -> PreparedTags:
    return _get_prepared_tags(story.tags)
