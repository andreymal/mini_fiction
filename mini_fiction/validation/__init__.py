#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy

import cerberus
from werkzeug.datastructures import FileStorage
from flask_babel import gettext, lazy_gettext

# when https://github.com/nicolaiarocci/cerberus/issues/174 will be solved, it can be rewritten


class ValidationError(ValueError):
    def __init__(self, errors):
        super().__init__()
        self.errors = errors

    def __str__(self):
        msgs = []
        for field, errors in self.errors.items():
            error_msg = ', '.join(str(x) for x in errors)
            msgs.append('{}: {}'.format(field, error_msg))
        return '; '.join(msgs)

    def __repr__(self):
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

        0x61: lazy_gettext("Field '{field}' cannot be coerced"),
        0x62: lazy_gettext("Field '{field}' cannot be renamed"),
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
    })

    def __init__(self, tree=None, custom_messages=None):
        super().__init__(tree)
        self.custom_messages = custom_messages or {}

    def format_message(self, field, error):
        tmp = self.custom_messages
        for i, x in enumerate(error.schema_path):
            try:
                tmp = tmp[x]
            except KeyError:
                if i == len(error.schema_path) - 1 and 'any' in tmp:
                    return tmp['any']
                return super().format_message(field, error)
        if isinstance(tmp, dict):
            return super().format_message(field, error)
        return tmp


class Validator(cerberus.Validator):
    """Usage:
    schema = {"name": {"minlength": 2, "error_messages": {"minlength": "Custom too few"}}}
    v = Validator(schema)
    v.validate({"q": "0"})  # => False
    v.errors  # => {'q': ['Custom too few']}
    """

    def __init__(self, *args, **kwargs):
        if args:
            if 'schema' in kwargs:
                raise TypeError("got multiple values for argument 'schema'")
            schema = args[0]
        else:
            schema = kwargs.pop('schema')

        if isinstance(schema, dict):
            schema = copy.deepcopy(schema)
            self.populate_custom_messages(schema)
            args = [schema] + list(args[1:])

        kwargs['error_handler'] = CustomErrorHandler(custom_messages=self.custom_messages)
        if 'purge_unknown' not in kwargs:
            kwargs['purge_unknown'] = True
        super().__init__(*args, **kwargs)
        self.custom_messages = {}
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

    def validated(self, document, *args, **kwargs):
        throw_exception = kwargs.pop('throw_exception', True)
        result = super().validated(document, *args, **kwargs)
        if result is None and throw_exception:
            raise ValidationError(self.errors)
        return result

    def _validate_allowed_func(self, allowed_func, field, value):
        """ {'nullable': False} """
        if allowed_func not in self._allowed_func_caches:
            self._allowed_func_caches[allowed_func] = allowed_func()
        choices = self._allowed_func_caches[allowed_func]
        if value not in choices:
            self._error(field, gettext("Unallowed value {value}").format(value=value))

    def _validate_type_file(self, value):
        return isinstance(value, FileStorage)

    def _validate_maxlength(self, max_length, field, value):
        """ {'type': 'integer'} """
        # Pony ORM автоматически strip'ает строки (если не указано иное),
        # так что автоматически strip'аем их и здесь для удобства
        if isinstance(value, str):
            if len(value.strip()) > max_length:
                self._error(field, lazy_gettext("Max length is {constraint}").format(constraint=max_length))
        else:
            super()._validate_maxlength(max_length, field, value)

    def _validate_minlength(self, min_length, field, value):
        """ {'type': 'integer'} """
        if isinstance(value, str):
            if len(value.strip()) < min_length:
                self._error(field, lazy_gettext("Min length is {constraint}").format(constraint=min_length))
        else:
            super()._validate_minlength(min_length, field, value)

    def _validate_maxlengthnostrip(self, max_length, field, value):
        """ {'type': 'integer'} """
        # Оставляем родной валидатор доступным
        super()._validate_maxlength(max_length, field, value)

    def _validate_minlengthnostrip(self, min_length, field, value):
        """ {'type': 'integer'} """
        super()._validate_minlength(min_length, field, value)
