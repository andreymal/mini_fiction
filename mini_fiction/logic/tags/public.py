from dataclasses import dataclass, field
from datetime import datetime
from operator import attrgetter
from typing import Collection, Dict, List, Literal, Optional, Tuple, Union

from flask_babel import LazyString, lazy_gettext
from pony.orm import desc

from mini_fiction.logic.adminlog import log_addition, log_changed_fields, log_deletion
from mini_fiction.logic.environment import get_cache
from mini_fiction.logic.tasks import schedule_task
from mini_fiction.models import Author, Story, StoryTag, StoryTagLog, Tag, TagCategory
from mini_fiction.validation import RawData, ValidationError, Validator
from mini_fiction.validation.tags import TAG
from mini_fiction.validation.utils import safe_string_coerce

from .private import (
    MAX_TAGS,
    PreparedTags,
    extract_spoilers,
    group_tags,
    make_alias_for,
    normalize_tag,
    set_blacklist,
    validate_tag_name,
)

TagsSortType = Literal["stories", "date", "name"]

TAG_SORTING: Dict[TagsSortType, Tuple[str, bool]] = {
    "stories": ("published_stories_count", True),
    "date": ("created_at", True),
    "name": ("iname", False),
}

TagsCreationRequest = Tuple[int, str, str]


@dataclass
class CategorizedTag:
    category: Optional[TagCategory] = None
    tags: List[Tag] = field(default_factory=list)


@dataclass
class TagsResponse:
    success: bool
    """All requested tags were found"""
    tags: List[Optional[Tag]]
    """Found tags in initial order of requested strings"""
    aliases: List[Tag]
    """Aliased tags that were replaced with canonical ones"""
    blacklisted: List[Tag]
    """Blocked tags"""
    invalid: List[Tuple[str, Union[str, LazyString]]]
    """List of invalid tags alongside with reasons"""
    created: List[Tag]
    """Created tags, if specified to do so"""
    nonexisting: List[str]
    """Strings without corresponding tags, when specified to not create tags"""


# pylint: disable=too-many-statements
def get_tags_objects(
    tags: Collection[Union[Tag, str]],
    should_create: bool = False,
    user: Optional[Author] = None,
) -> TagsResponse:
    """
    Если скормить несколько одинаковых тегов, то в списке tags могут
    появиться дубликаты.
    """

    # Достаём список строк для поиска тегов
    tags_search = [x for x in tags if not isinstance(x, Tag)]
    tags_db = {x.iname: x for x in tags if isinstance(x, Tag)}

    # Ищем недостающие теги в базе
    inames_opt = [normalize_tag(x) for x in tags_search]
    inames = [x for x in inames_opt if x]
    if inames:
        # Алгоритм сравнения строк в БД может отличаться от такового в Python,
        # из-за чего при запросе всех тегов одним запросом будет проблематично
        # сопоставить теги из базы с исходными iname — например, MySQL/MariaDB
        # с utf8mb4_general_ci считает буквы «е» и «ё» одинаковыми.
        # Поэтому запрашиваем теги из базы поштучно, чтобы обойтись
        # без сравнения строк в этом коде.
        # См. также https://github.com/ponyorm/pony/issues/452
        for iname in inames:
            existing_tag = Tag.get(iname=iname)
            if existing_tag:
                tags_db[iname] = existing_tag
                # iname из базы может отличаться от исходного iname
                tags_db[existing_tag.iname] = existing_tag

    result = TagsResponse(
        success=True,
        tags=[None] * len(tags),
        aliases=[],
        blacklisted=[],
        invalid=[],
        created=[],
        nonexisting=[],
    )

    create_tags: List[TagsCreationRequest] = []  # [(index, name, iname), ...]

    # Анализируем каждый запрошенный тег
    for i, possible_tag in enumerate(tags):
        if isinstance(possible_tag, Tag):
            raw_name = name = possible_tag.name
            iname = possible_tag.iname
            tag = possible_tag
        else:
            raw_name = possible_tag
            name = safe_string_coerce(possible_tag.strip())
            iname = normalize_tag(name)
            tag = None
            if iname:
                # Check, if such tag even exists
                tag = tags_db.get(iname)
                assert iname == normalize_tag(possible_tag)

        if tag is not None:
            # Если тег существует, проверяем, что его можно использовать
            if tag.is_alias_for:
                if tag.is_alias_for.is_alias_for:
                    raise RuntimeError(
                        f"Tag alias {tag.id} refers to another alias {tag.is_alias_for.id}!"
                    )
                result.aliases.append(tag)
                tag = tag.is_alias_for
            if tag.is_blacklisted:
                result.blacklisted.append(tag)
                result.success = False
                tag = None

        elif should_create:
            # Если не существует — создаём
            if not user or not user.is_authenticated:
                raise ValueError("Not authenticated")
            reason = validate_tag_name(name)
            if reason is not None:
                result.invalid.append((raw_name, reason))
                result.success = False
            else:
                if iname is not None:
                    create_tags.append((i, name, iname))  # Отложенное создание тегов
                else:
                    result.invalid.append((name, lazy_gettext("No such tag")))
        else:
            result.nonexisting.append(raw_name)
            result.success = False

        if tag:
            result.tags[i] = tag

    # Если нужно создать теги, то создаём их только при отсутствии других
    # ошибок, чтобы зазря не мусорить в базу данных
    if create_tags and result.success:
        for i, name, iname in create_tags:
            if iname in tags_db:
                # На случай, если пользователь пропихнул дублирующиеся теги
                result.tags[i] = tags_db[iname]
                continue
            tag = Tag(name=name, iname=iname, created_by=user)
            tag.flush()  # получаем id у базы данных
            tags_db[
                tag.iname
            ] = tag  # На случай, если у следующего тега в цикле совпадёт iname
            result.created.append(tag)
            result.tags[i] = tag

        get_cache().delete("tags_autocomplete_default")

    return result


def get_all_tags(*, sort: TagsSortType) -> List[Tag]:
    sorting_field, reverse = TAG_SORTING[sort]
    return sorted(
        Tag.select()
        .filter(lambda x: not x.is_blacklisted and not x.is_alias)
        .prefetch(Tag.category),
        key=attrgetter(sorting_field),
        reverse=reverse,
    )


def get_tags_with_categories(sort: TagsSortType = "name") -> List[CategorizedTag]:
    tags = get_all_tags(sort=sort)

    categories_dict: Dict[int, CategorizedTag] = {}
    others = CategorizedTag()
    for tag in tags:
        if not tag.category:
            others.tags.append(tag)
            continue
        if tag.category.id not in categories_dict:
            categories_dict[tag.category.id] = CategorizedTag(
                category=tag.category, tags=[]
            )
        categories_dict[tag.category.id].tags.append(tag)

    result = sorted(
        categories_dict.values(), key=lambda x: x.category.id if x.category else 0
    )
    result.append(others)
    return result


###


def search_by_prefix(name: str, limit: int = 20) -> List[Tag]:
    iname = normalize_tag(name)
    if iname is None or limit < 1:
        return []
    limit = min(limit, 100)
    result = []

    # Ищем точное совпадение
    exact_tag = Tag.get(iname=iname, is_alias_for=None, reason_to_blacklist="")
    if exact_tag:
        result.append(exact_tag)
    else:
        tag_alias = Tag.get(iname=iname, reason_to_blacklist="")
        if tag_alias:
            exact_tag = tag_alias.is_alias_for
            assert exact_tag is not None
            result.append(exact_tag)

    # Ищем остальные теги по префиксу
    if len(result) < limit:
        tags = set(
            Tag.select(
                lambda x: x.iname.startswith(iname)  # type: ignore
                and not x.is_alias
                and not x.is_blacklisted
            ).sort_by(desc(Tag.published_stories_count))[: limit + len(result)]
        )
        # Подключаем синонимы отдельным запросом, чтоб были по порядку ниже несинонимов)
        tags = tags | set(
            Tag.select(
                lambda x: x.iname.startswith(iname)  # type: ignore
                and x.is_alias
                and not x.is_blacklisted
            )
        )
        tags = sorted(tags, key=lambda x: x.published_stories_count, reverse=True)
        result.extend([x for x in tags if x not in result])

    return result[:limit]


def get_aliases_for(
    tags: Collection[Tag], hidden: bool = False
) -> Dict[int, List[Tag]]:
    for tag in tags:
        if tag.is_alias or tag.is_blacklisted:
            raise ValueError(
                "Only valid canonical tags are allowed for get_aliases_for"
            )

    result = {x.id: [] for x in tags}
    query = Tag.select(lambda x: x.is_alias_for in tags)
    if not hidden:
        query = query.filter(lambda x: not x.is_hidden_alias)
    for ts in query:
        # SAFETY: Selected only tags with aliases
        result[ts.is_alias_for.id].append(ts)  # type: ignore
    return result


def create(user: Optional[Author], data: RawData) -> Tag:
    if not user or not user.is_staff:
        raise ValueError("Not authorized")

    data = Validator(TAG).validated(data)

    errors = {}

    bad_reason = validate_tag_name(data["name"])
    if bad_reason:
        errors["name"] = [bad_reason]

    iname = normalize_tag(data["name"])
    if not bad_reason and Tag.get(iname=iname):
        errors["name"] = [lazy_gettext("Tag already exists")]

    canonical_tag = None
    if data.get("is_alias_for"):
        canonical_tag = Tag.get(iname=normalize_tag(data["is_alias_for"]))
        if not canonical_tag:
            errors["is_alias_for"] = [lazy_gettext("Tag not found")]

    if errors:
        raise ValidationError(errors)

    tag = Tag(
        name=data["name"],
        iname=iname,
        category=data.get("category"),
        description=data.get("description") or "",
        is_spoiler=data.get("is_spoiler", False),
        created_by=user,
        is_alias_for=None,
        reason_to_blacklist="",
    )
    tag.flush()

    log_addition(by=user, what=tag)

    if data.get("reason_to_blacklist"):
        set_blacklist(tag, user, data["reason_to_blacklist"])
    elif canonical_tag:
        make_alias_for(
            tag, user, canonical_tag, hidden=data.get("is_hidden_alias", False)
        )

    return tag


def update(tag: Tag, user: Optional[Author], data: RawData) -> None:
    if not user or not user.is_staff:
        raise ValueError("Not authorized")

    data = Validator(TAG).validated(data, update=True)
    changes = {}
    errors = {}

    if "name" in data and data["name"] != tag.name:
        bad_reason = validate_tag_name(data["name"])
        if bad_reason:
            errors["name"] = [bad_reason]

        iname = normalize_tag(data["name"])
        if not bad_reason and iname != tag.iname and Tag.get(iname=iname):
            errors["name"] = [lazy_gettext("Tag already exists")]

        changes["name"] = data["name"]
        if iname != tag.iname:
            changes["iname"] = iname

    if "category" in data:
        old_category_id = tag.category.id if tag.category else None
        if old_category_id != data["category"]:
            changes["category"] = data["category"]

    for key in ("description", "is_spoiler", "is_extreme_tag"):
        if key in data and data[key] != getattr(tag, key):
            changes[key] = data[key]

    canonical_tag = tag.is_alias_for
    if "is_alias_for" in data:
        if data.get("is_alias_for"):
            canonical_tag = Tag.get(iname=normalize_tag(data["is_alias_for"]))
            if not canonical_tag:
                errors["is_alias_for"] = [lazy_gettext("Tag not found")]
            elif (
                canonical_tag == tag
                or canonical_tag.is_alias_for
                and canonical_tag.is_alias_for == tag
            ):
                errors["is_alias_for"] = [lazy_gettext("Tag cannot refer to itself")]
        else:
            canonical_tag = None

    if errors:
        raise ValidationError(errors)
    if changes:
        changes["updated_at"] = datetime.utcnow()
        tag.set(**changes)

        log_changed_fields(by=user, what=tag, fields=set(changes) - {"updated_at"})

    if "reason_to_blacklist" in data:
        set_blacklist(tag, user, data["reason_to_blacklist"])
    if not tag.is_blacklisted and ("is_alias_for" in data or "is_hidden_alias" in data):
        make_alias_for(
            tag, user, canonical_tag, data.get("is_hidden_alias", tag.is_hidden_alias)
        )


def delete(tag: Tag, user: Optional[Author]) -> None:
    if not user or not user.is_staff:
        raise ValueError("Not authorized")

    tm = datetime.utcnow()

    story_tags = list(StoryTag.select(lambda x: x.tag == tag).prefetch(StoryTag.story))
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

    log_deletion(by=user, what=tag)
    tag.delete()


def _get_prepared_tags(story_tags: Collection[StoryTag]) -> PreparedTags:
    sorted_tags: List[Tag] = sorted(
        (st.tag for st in story_tags), key=attrgetter("category", "iname")
    )
    main_tags, spoiler = extract_spoilers(sorted_tags)
    extreme = [t for t in sorted_tags if t.is_extreme_tag]

    if len(main_tags) <= MAX_TAGS:
        return PreparedTags(
            primary=main_tags,
            secondary=[],
            extreme=extreme,
            spoiler=spoiler,
        )
    primary, secondary = group_tags(main_tags)
    return PreparedTags(
        primary=primary,
        secondary=secondary,
        extreme=extreme,
        spoiler=spoiler,
    )


def get_prepared_tags(story: Story) -> PreparedTags:
    return _get_prepared_tags(story.tags)
