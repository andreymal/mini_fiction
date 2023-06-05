import re
import copy
from collections.abc import Iterable
from typing import Any, Dict, List, Union

import cerberus
from werkzeug.datastructures import FileStorage
from flask_babel import gettext, lazy_gettext
from flask_babel.speaklater import LazyString

# when https://github.com/nicolaiarocci/cerberus/issues/174 will be solved, it can be rewritten


MIN_LENGTH_NOSTRIP = cerberus.errors.ErrorDefinition(0x4127, 'minlengthnostrip')
MAX_LENGTH_NOSTRIP = cerberus.errors.ErrorDefinition(0x4128, 'maxlengthnostrip')
DYNREGEX_MISMATCH = cerberus.errors.ErrorDefinition(0x4141, 'dynregex')

file_type = cerberus.TypeDefinition('file', (FileStorage,), ())

RawData = Dict[str, Any]
ValidatedData = Dict[str, Any]


class ValidationError(ValueError):
    def __init__(self, errors: Dict[str, List[Union[str, LazyString]]]):
        super().__init__()
        self.errors = errors
        if not isinstance(errors, dict):
            raise TypeError('errors must be dict')

    def __str__(self):  # pragma: no cover
        return self._str_value(self.errors)[:-2]

    def _str_value(self, e):
        if isinstance(e, list):
            return ', '.join(str(x) for x in e)
        if not isinstance(e, dict):
            return str(e)
        return '; '.join(
            '{}: {}'.format(k, self._str_value(v))
            for k, v in sorted(e.items())
        ) + '; '

    def __repr__(self):  # pragma: no cover
        return 'ValidationError({})'.format(repr(self.errors))


class CustomErrorHandler(cerberus.errors.BasicErrorHandler):
    messages = cerberus.errors.BasicErrorHandler.messages.copy()
    messages.update({
        0x02: lazy_gettext("Required field"),
        0x03: lazy_gettext("Unknown field"),
        0x04: lazy_gettext("Field '{0}' is required"),
        0x05: lazy_gettext("Depends on these values: {constraint}"),
        0x06: lazy_gettext("{0} must not be present with '{field}'"),

        0x21: lazy_gettext("'{0}' is not a document, must be a dict"),
        0x22: lazy_gettext("Field should not be empty"),
        0x23: lazy_gettext("Field should not be empty"),
        0x24: lazy_gettext("Must be of {constraint} type"),
        0x26: lazy_gettext("Length of list should be {constraint}, it is {0}"),
        0x27: lazy_gettext("Min length is {constraint}"),
        0x28: lazy_gettext("Max length is {constraint}"),

        0x41: lazy_gettext("Value does not match regex '{constraint}'"),
        0x42: lazy_gettext("Min value is {constraint}"),
        0x43: lazy_gettext("Max value is {constraint}"),
        0x44: lazy_gettext("Unallowed value {value}"),
        0x45: lazy_gettext("Unallowed values {0}"),
        0x46: lazy_gettext("Unallowed value {value}"),
        0x47: lazy_gettext("Unallowed values {0}"),

        0x61: lazy_gettext("Field '{field}' cannot be coerced: {0}"),
        0x62: lazy_gettext("Field '{field}' cannot be renamed: {0}"),
        0x63: lazy_gettext("Field is read-only"),
        0x64: lazy_gettext("Default value for '{field}' cannot be set: {0}"),

        0x81: lazy_gettext("Mapping doesn't validate subschema: {0}"),
        0x82: lazy_gettext("One or more sequence-items don't validate: {0}"),
        0x83: lazy_gettext("One or more properties of a mapping  don't validate: {0}"),
        0x84: lazy_gettext("One or more values in a mapping don't validate: {0}"),
        0x85: lazy_gettext("One or more sequence-items don't validate: {0}"),

        0x91: lazy_gettext("One or more definitions validate"),
        0x92: lazy_gettext("None or more than one rule validate"),
        0x93: lazy_gettext("No definitions validate"),
        0x94: lazy_gettext("One or more definitions don't validate"),

        0x4127: lazy_gettext("Min length is {constraint}"),
        0x4128: lazy_gettext("Max length is {constraint}"),
        0x4141: lazy_gettext("Value does not match regex '{0}'"),
    })

    def __init__(self, tree=None, custom_messages=None):
        super().__init__(tree)
        self.custom_messages = custom_messages or {}

    def _format_message(self, field, error):
        # Собираем аргументы для форматирования сообщения об ошибке
        fmt_args = error.info
        fmt_kwargs = {'constraint': error.constraint, 'field': field, 'value': error.value}

        custom_msg = None

        # Пробегаемся по кастомным сообщениям согласно пути к правилу в schema_path
        # (для кастомных правил schema_path пуст, если не использовать
        # ErrorDefinition, поэтому он тут используется, хоть и плохо
        # документирован в Cerberus)
        tmp = self.custom_messages
        for i, x in enumerate(error.schema_path):
            try:
                # Шажок
                tmp = tmp[x]
            except KeyError:
                # Шажок не удался, упёрлись
                # Если мы достигли места назначения (правила, выдавшего ошибку),
                # то берём его универсальное сообщение об ошибке
                if i == len(error.schema_path) - 1 and 'any' in tmp:
                    custom_msg = tmp['any']
                break

        # Если в цикле выше не упёрлись, то в tmp будет или сообщение об ошибке,
        # или, если не дошагали, словарь-кусок схемы
        if custom_msg is None:
            if isinstance(tmp, dict):
                # Если сообщения нет, возвращаем родное сообщение
                return super()._format_message(field, error)
            custom_msg = tmp

        # Сообщение может быть функцией, чтобы генерировать его динамически
        if callable(custom_msg):
            custom_msg = custom_msg()

        # Форматируем. Обёрнуто в str() ради всяких lazy_gettext
        return str(custom_msg).format(*fmt_args, **fmt_kwargs)


class Validator(cerberus.Validator):
    """Usage:
    schema = {"name": {"minlength": 2, "error_messages": {"minlength": "Custom too few"}}}
    v = Validator(schema)
    v.validate({"q": "0"})  # => False
    v.errors  # => {'q': ['Custom too few']}
    v.validated({"q": "0"})  # => ValidationError
    """

    types_mapping = cerberus.Validator.types_mapping.copy()
    types_mapping['file'] = file_type

    def __init__(self, *args, **kwargs) -> None:
        if args:
            if 'schema' in kwargs:  # pragma: no cover
                raise TypeError("got multiple values for argument 'schema'")
            schema = args[0]
        else:
            schema = kwargs.pop('schema')

        self.custom_messages = {}
        if isinstance(schema, dict):
            schema = copy.deepcopy(schema)
            self.populate_custom_messages(schema)
            args = [schema] + list(args[1:])

        kwargs['error_handler'] = CustomErrorHandler(custom_messages=self.custom_messages)
        if 'purge_unknown' not in kwargs:
            kwargs['purge_unknown'] = True
        super().__init__(*args, **kwargs)
        self._allowed_func_caches = {}

    def populate_custom_messages(self, schema):
        self.custom_messages = {}
        queue = [(schema, self.custom_messages)]
        while queue:
            item, msgs = queue.pop()
            if 'error_messages' in item:
                assert isinstance(item['error_messages'], dict)
                msgs.update(item.pop('error_messages'))
            for k, v in item.items():
                if isinstance(v, dict):
                    msgs[k] = {}
                    queue.append((v, msgs[k]))

    def validated(self, *args, **kwargs) -> ValidatedData:
        throw_exception = kwargs.pop('throw_exception', True)
        result = super().validated(*args, **kwargs)
        if result is None and throw_exception:
            raise ValidationError(self.errors)
        return result

    def _validate_allowed_func(self, allowed_func, field, value):
        """ {'nullable': False} """
        if allowed_func not in self._allowed_func_caches:
            self._allowed_func_caches[allowed_func] = set(allowed_func())
        choices = self._allowed_func_caches[allowed_func]
        if value not in choices:
            self._error(field, gettext("Unallowed value {value}").format(value=value))

    def _validate_maxlength(self, max_length, field, value):
        """ {'type': 'integer'} """
        # Pony ORM автоматически strip'ает строки (если не указано иное),
        # так что автоматически strip'аем их и здесь для удобства
        if isinstance(value, str):
            if len(value.strip()) > max_length:
                self._error(field, cerberus.errors.MAX_LENGTH, len(value.strip()))
        else:
            super()._validate_maxlength(max_length, field, value)

    def _validate_minlength(self, min_length, field, value):
        """ {'type': 'integer'} """
        if isinstance(value, str):
            if len(value.strip()) < min_length:
                self._error(field, cerberus.errors.MIN_LENGTH, len(value.strip()))
        else:
            super()._validate_minlength(min_length, field, value)

    def _validate_maxlengthnostrip(self, max_length, field, value):
        """ {'type': 'integer'} """
        # Оставляем родной валидатор доступным
        if isinstance(value, Iterable) and len(value) > max_length:
            self._error(field, MAX_LENGTH_NOSTRIP, len(value))

    def _validate_minlengthnostrip(self, min_length, field, value):
        """ {'type': 'integer'} """
        if isinstance(value, Iterable) and len(value) < min_length:
            self._error(field, MIN_LENGTH_NOSTRIP, len(value))

    def _validate_dynregex(self, pattern_func, field, value):
        """ {'nullable': False} """
        if not isinstance(value, str):
            return
        pattern = pattern_func()
        re_obj = re.compile(pattern)
        if not re_obj.fullmatch(value):
            self._error(field, DYNREGEX_MISMATCH, pattern)

    def _normalize_coerce_strip(self, value):
        if isinstance(value, str):
            return value.strip()
        return value
