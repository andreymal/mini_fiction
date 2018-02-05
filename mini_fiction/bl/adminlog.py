#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.bl.utils import BaseBL
from mini_fiction.validation import ValidationError

_types_cache = {}  # {str: id}
_types_cache_rev = {}  # {id: str}


class AdminLogBL(BaseBL):
    def create(self, user, obj, action, fields=None, change_message=None):
        from mini_fiction.models import AdminLog

        if action not in (
            AdminLog.ADDITION, AdminLog.CHANGE, AdminLog.DELETION
        ):
            raise ValidationError({'action': ['Invalid action']})

        if change_message is None:
            if fields is None and action == AdminLog.CHANGE:
                raise ValidationError({'fields': ['Please set fields or change_message']})
            change_message = ''
            if fields:
                # Срисовал из джанги 1.5
                msg = ['Изменен ']
                for i, f in enumerate(fields):
                    if i > 0:
                        msg.append(' и ' if i == len(fields) - 1 else ', ')
                    msg.append(f)
                msg.append('.')
                change_message = ''.join(msg)
                del msg

        type_str = str(obj.__class__.__name__).lower()
        type_id = self.get_or_create_type_id(type_str)

        logitem = AdminLog(
            user=user,
            type=type_id,
            object_id=str(obj.get_pk()),
            object_repr=str(obj),
            action_flag=action,
            change_message=change_message,
        )
        logitem.flush()
        return logitem

    def get_or_create_type_id(self, type_str):
        from mini_fiction.models import AdminLogType

        if type_str in _types_cache:
            return _types_cache[type_str]

        self._load_type_cache()

        if type_str in _types_cache:
            return _types_cache[type_str]

        new_type = AdminLogType(model=type_str)
        new_type.flush()
        _types_cache[type_str] = new_type.id
        _types_cache_rev[new_type.id] = type_str
        return new_type.id

    def _load_type_cache(self):
        from mini_fiction.models import AdminLogType

        _types_cache.clear()
        _types_cache.update(
            {x.model: x.id for x in AdminLogType.select()}
        )

        _types_cache_rev.clear()
        _types_cache_rev.update(
            {v: k for k, v in _types_cache.items()}
        )
