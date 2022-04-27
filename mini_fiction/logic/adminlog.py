import ast
import datetime
from enum import IntEnum
from typing import Collection, Dict, List, Optional, Tuple, Union, TypedDict

from flask import url_for
from pony.orm.core import Entity

from mini_fiction.models import AdminLog, AdminLogType, Author

_types_cache: Dict[str, int] = {}
_types_cache_rev: Dict[int, str] = {}

ObjectPrimaryKey = Union[int, Tuple[int, Union[int, str]]]


class RenderedLogUser(TypedDict):
    id: int  # noqa: VNE003
    username: str


class RenderedLogItem(TypedDict):
    id: int  # noqa: VNE003
    user: Optional[RenderedLogUser]
    type: int  # noqa: VNE003
    type_str: str
    object_id: ObjectPrimaryKey
    object_id_str: str
    object_repr: str
    action_flag: str
    change_message: str
    action_time: datetime.datetime
    admin_url: Optional[str]


class RenderedLog(TypedDict):
    count: int
    items: List[RenderedLogItem]


class AdminLogActionKind(IntEnum):
    ADDITION = 1
    CHANGE = 2
    DELETION = 3


# pylint: disable=too-many-return-statements
def _get_object_url(typ: str, pk: ObjectPrimaryKey) -> Optional[str]:
    if typ == "abusereport":
        return url_for("admin_abuse_reports.show", abuse_id=pk)
    if typ == "author":
        return url_for("admin_authors.update", pk=pk)
    if typ == "character":
        return url_for("admin_characters.update", pk=pk)
    if typ == "charactergroup":
        return url_for("admin_charactergroups.update", pk=pk)
    if typ == "htmlblock" and isinstance(pk, tuple):
        return url_for("admin_htmlblocks.update", name=pk[0], lang=pk[1])
    if typ == "logopic":
        return url_for("admin_logopics.update", pk=pk)
    if typ == "newsitem":
        return url_for("admin_news.update", pk=pk)
    if typ == "staticpage" and isinstance(pk, tuple):
        return url_for("admin_staticpages.update", name=pk[0], lang=pk[1])
    if typ == "tagcategory":
        return url_for("admin_tag_categories.update", pk=pk)
    if typ == "tag":
        return url_for("admin_tags.update", pk=pk)
    return None


def load_logs_type_cache() -> None:
    _types_cache.clear()
    _types_cache.update({x.model: x.id for x in AdminLogType.select()})

    _types_cache_rev.clear()
    _types_cache_rev.update({v: k for k, v in _types_cache.items()})


def get_list(offset: int = 0, limit: int = 20, order_desc: bool = True) -> RenderedLog:
    limit = max(1, min(limit, 1000))

    objects = AdminLog.select()
    if order_desc:
        objects = objects.order_by(AdminLog.id.desc())
    else:
        objects = objects.order_by(AdminLog.id)

    count = objects.count()
    to = offset + limit
    objects = objects.prefetch(AdminLog.user)[offset:to]

    result: List[RenderedLogItem] = []
    for obj in objects:
        if obj.type.id not in _types_cache_rev:
            load_logs_type_cache()
        type_str = _types_cache_rev.get(obj.type.id, "N/A")

        object_id = ast.literal_eval(obj.object_id)

        item: RenderedLogItem = {
            "id": obj.id,
            "user": {
                "id": obj.user.id,
                "username": obj.user.username,
            }
            if obj.user
            else None,
            "type": obj.type.id,
            "type_str": type_str,
            "object_id": ast.literal_eval(obj.object_id),
            "object_id_str": obj.object_id,
            "object_repr": obj.object_repr,
            "action_flag": obj.action_flag,
            "change_message": obj.change_message,
            "action_time": obj.action_time,
            "admin_url": _get_object_url(type_str, object_id),
        }

        result.append(item)

    return {"count": count, "items": result}


def _get_or_create_type_id(type_str: str) -> int:
    if type_str in _types_cache:
        return _types_cache[type_str]

    load_logs_type_cache()

    if type_str in _types_cache:
        return _types_cache[type_str]

    new_type = AdminLogType(model=type_str)
    new_type.flush()
    _types_cache[type_str] = new_type.id
    _types_cache_rev[new_type.id] = type_str
    return new_type.id


def _generate_change_message(fields: Collection[str]) -> str:
    msg = ["Изменен "]
    for index, field in enumerate(fields):
        if index > 0:
            msg.append(" и " if index == len(fields) - 1 else ", ")
        msg.append(field)
    msg.append(".")
    return "".join(msg)


def _log_event(
    *,
    by: Author,
    what: Entity,
    action: AdminLogActionKind,
    change_message: str = "",
) -> None:
    type_str = str(what.__class__.__name__).lower()
    type_id = _get_or_create_type_id(type_str)

    AdminLog(
        user=by,
        type=type_id,
        object_id=str(what.get_pk()),
        object_repr=str(what),
        action_flag=action.value,
        change_message=change_message,
    ).flush()


def log_addition(*, by: Author, what: Entity) -> None:
    _log_event(
        by=by,
        what=what,
        action=AdminLogActionKind.ADDITION,
    )


def log_deletion(*, by: Author, what: Entity) -> None:
    _log_event(
        by=by,
        what=what,
        action=AdminLogActionKind.DELETION,
    )


def log_changed_fields(*, by: Author, what: Entity, fields: Collection[str]) -> None:
    message = _generate_change_message(fields)
    _log_event(
        by=by,
        what=what,
        change_message=message,
        action=AdminLogActionKind.CHANGE,
    )


def log_changed_generic(*, by: Author, what: Entity, message: str) -> None:
    _log_event(
        by=by,
        what=what,
        change_message=message,
        action=AdminLogActionKind.CHANGE,
    )
