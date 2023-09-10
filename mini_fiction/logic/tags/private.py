import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import chain, islice
from typing import List, Optional, Tuple

from flask_babel import lazy_gettext
from pony import orm

from mini_fiction.logic.adminlog import log_changed_fields, log_changed_generic
from mini_fiction.logic.environment import get_settings
from mini_fiction.logic.tasks import schedule_task
from mini_fiction.models import Author, StoryTag, StoryTagLog, Tag
from mini_fiction.validation.utils import safe_string_coerce

MAX_TAGS = 5


@dataclass
class PreparedTags:
    primary: List[Tag]
    secondary: List[Tag]
    extreme: List[Tag]
    spoiler: List[Tag]


def normalize_tag(tag_name: Optional[str]) -> Optional[str]:
    if not tag_name:
        return None

    whitelist = get_settings().NORMALIZED_TAGS_WHITELIST
    delimiters = get_settings().NORMALIZED_TAGS_DELIMETERS

    tag_name = "".join(
        (
            x if x in whitelist else ("_" if x in delimiters else "")
            for x in safe_string_coerce(tag_name.lower()).strip()
        )
    )
    while "__" in tag_name:
        tag_name = tag_name.replace("__", "_")
    return tag_name.strip("_")[:32] or None


def make_alias_for(
    tag: Tag,
    user: Optional[Author],
    canonical_tag: Optional[Tag],
    hidden: bool = False,
) -> None:
    if not user or not user.is_staff:
        raise ValueError("Not authorized")

    if canonical_tag and canonical_tag.is_alias_for:
        if canonical_tag.is_alias_for.is_alias_for:
            raise RuntimeError(
                f"Tag alias {canonical_tag.id} refers to another alias {canonical_tag.is_alias_for.id}!"
            )
        canonical_tag = canonical_tag.is_alias_for

    if tag.is_alias_for == canonical_tag:
        if canonical_tag and bool(hidden) != tag.is_hidden_alias:
            tag.is_hidden_alias = bool(hidden)
            tag.updated_at = datetime.utcnow()
            log_changed_fields(by=user, what=tag, fields=("is_hidden_alias",))
        return

    tm = datetime.utcnow()

    if canonical_tag:
        if canonical_tag == tag:
            raise RuntimeError("Self-reference!")

        tag.is_alias_for = canonical_tag
        tag.is_hidden_alias = bool(hidden)

        story_tags = list(
            StoryTag.select(lambda x: x.tag == tag).prefetch(StoryTag.story)
        )
        stories_with_canonical_tag = list(
            orm.select(x.story.id for x in StoryTag if x.tag == canonical_tag)
        )
        for st in story_tags:
            StoryTagLog(
                story=st.story.id,
                tag=tag,
                tag_name=tag.name,
                action_flag=StoryTagLog.DELETION,
                modified_by=user,
                date=tm,
            ).flush()
            if st.story.id not in stories_with_canonical_tag:
                StoryTagLog(
                    story=st.story.id,
                    tag=canonical_tag,
                    tag_name=canonical_tag.name,
                    action_flag=StoryTagLog.ADDITION,
                    modified_by=user,
                    date=tm,
                ).flush()
                st.tag = canonical_tag
                st.flush()
                canonical_tag.stories_count += 1
                if st.story.published:
                    canonical_tag.published_stories_count += 1
            else:
                st.delete()
            schedule_task(
                "sphinx_update_story",
                st.story.id,
                ("tag",),
            )
            tag.stories_count -= 1
            if st.story.published:
                tag.published_stories_count -= 1

    else:
        tag.is_alias_for = None
        tag.is_hidden_alias = False

    tag.updated_at = tm

    if tag.is_alias_for:
        log_message = f"Тег стал синонимом тега «{tag.is_alias_for.name}»."
    else:
        log_message = "Тег перестал быть синонимом."
    log_changed_generic(by=user, what=tag, message=log_message)


def set_blacklist(tag: Tag, user: Optional[Author], reason: Optional[str]) -> None:
    if not user or not user.is_staff:
        raise ValueError("Not authorized")

    if reason == tag.reason_to_blacklist:
        return

    old_reason = tag.reason_to_blacklist
    tm = datetime.utcnow()

    if reason:
        tag.reason_to_blacklist = reason
        tag.is_alias_for = None
        tag.is_hidden_alias = False

        story_tags = list(
            StoryTag.select(lambda x: x.tag == tag).prefetch(StoryTag.story)
        )
        for st in story_tags:
            StoryTagLog(
                story=st.story.id,
                tag=tag,
                tag_name=tag.name,
                action_flag=StoryTagLog.DELETION,
                modified_by=user,
                date=tm,
            ).flush()
            schedule_task(
                "sphinx_update_story",
                st.story.id,
                ("tag",),
            )
            st.delete()
            tag.stories_count -= 1
            if st.story.published:
                tag.published_stories_count -= 1

    else:
        tag.reason_to_blacklist = ""

    tag.updated_at = tm

    if tag.reason_to_blacklist and old_reason:
        log_message = "Изменена причина попадания тега в чёрный список."
    elif tag.reason_to_blacklist:
        log_message = "Тег добавлен в чёрный список."
    else:
        log_message = "Тег убран из чёрного списка."
    log_changed_generic(by=user, what=tag, message=log_message)


def validate_tag_name(raw_tag_name: str) -> Optional[str]:
    iname = normalize_tag(raw_tag_name)
    if not iname:
        return lazy_gettext("Empty tag")

    for regex, reason in get_settings().TAGS_BLACKLIST_REGEX.items():
        if re.search(regex, iname, flags=re.IGNORECASE):
            return str(reason)

    return None


def extract_spoilers(tags: List[Tag]) -> Tuple[List[Tag], List[Tag]]:
    result = defaultdict(list)
    for tag in tags:
        result[tag.is_spoiler].append(tag)
    return result.get(False, []), result.get(True, [])


def group_tags(tags: List[Tag]) -> Tuple[List[Tag], List[Tag]]:
    grouped = defaultdict(list)
    for tag in tags:
        grouped[tag.category].append(tag)

    primary: List[Tag] = []
    for tag_group in islice(grouped.values(), 0, MAX_TAGS):
        primary.append(tag_group.pop(0))

    secondary = list(chain.from_iterable(grouped.values()))

    return primary, secondary
