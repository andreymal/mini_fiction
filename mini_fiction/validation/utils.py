#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Собираем список сомнительных символов, чтобы вычищать их при валидации,
# ибо нефиг. \r попутно тоже вычищаем за ненадобностью, \n и \t оставляем
unsafe_chars = [chr(x) for x in range(32) if x not in (9, 10,)]
unsafe_chars += [chr(x) for x in range(127, 160)]
unsafe_chars += ['\ufffe', '\ufeff', '\uffff']
unsafe_chars = ''.join(unsafe_chars)


def as_required(schema, only=None, exclude=None, keep_defaults=False, defaults=None, **kwargs):
    '''Делает параметры в схеме обязательными. Возвращает обработанную копию
    схемы. Обрабатывает только верхний уровень.

    :param dict schema: обрабатываемая схема
    :param list only: если указан, будут обрабатываться только параметры,
      указанные в этом списке
    :param list exclude: если указан, поля из этого списка не будут
      обрабатываться
    :param bool keep_defaults: если True, то оставляет значения по умолчанию
      в покое при их отсутствии в аргументах defaults и default; иначе
      значение по умолчанию удаляется при его наличии в исходной схеме
    :param dict defaults: словарь со значениями по умолчанию; имеет приоритет
      над default
    :param default: если указан, пропишется данное значение по умолчанию
    '''

    if tuple(kwargs) not in ((), ('default',)):
        raise TypeError('as_required() got an unexpected keyword arguments')

    if keep_defaults and 'default' in kwargs:
        raise ValueError("Cannot use 'keep_defaults' and 'default' together")

    new_schema = {}

    for k, v in schema.items():
        v = dict(v)
        new_schema[k] = v

        if only is not None and k not in only:
            continue
        if exclude is not None and k in exclude:
            continue

        v['required'] = True
        if defaults and k in defaults:
            v['default'] = defaults[k]
        elif 'default' in kwargs:
            v['default'] = kwargs['default']
        elif not keep_defaults:
            v.pop('default', None)

    return new_schema


def as_optional(schema, only=None, exclude=None, keep_defaults=False, defaults=None, **kwargs):
    '''Делает параметры в схеме опциональными. Полезно для функций,
    занимающихся обновлением чего-нибудь (более функциональный аналог родного
    validate(update=True) из Cerberus). Возвращает обработанную копию схемы.
    Обрабатывает только верхний уровень.

    :param dict schema: обрабатываемая схема
    :param list only: если указан, будут обрабатываться только параметры,
      указанные в этом списке
    :param list exclude: если указан, поля из этого списка не будут
      обрабатываться
    :param bool keep_defaults: если True, то оставляет значения по умолчанию
      в покое при их отсутствии в аргументах defaults и default; иначе
      значение по умолчанию удаляется при его наличии в исходной схеме
    :param dict defaults: словарь со значениями по умолчанию; имеет приоритет
      над default
    :param default: если указан, пропишется данное значение по умолчанию
    '''

    if tuple(kwargs) not in ((), ('default',)):
        raise TypeError('as_optional() got an unexpected keyword arguments')

    if keep_defaults and 'default' in kwargs:
        raise ValueError("Cannot use 'keep_defaults' and 'default' together")

    new_schema = {}

    for k, v in schema.items():
        v = dict(v)
        new_schema[k] = v

        if only is not None and k not in only:
            continue
        if exclude is not None and k in exclude:
            continue

        v['required'] = False
        if defaults and k in defaults:
            v['default'] = defaults[k]
        elif 'default' in kwargs:
            v['default'] = kwargs['default']
        elif not keep_defaults:
            v.pop('default', None)

    return new_schema


def uniondict(d1, d2):
    result = dict(d1)
    result.update(d2)
    return result


def bool_coerce(v):
    if v in (True, 1, '1', 'y', 'Y', 'on', 'true'):
        return True
    if v in (False, 0, '0', 'n', 'N', 'off', 'false', ''):
        return False
    raise ValueError


def clean_string(s, drop_chars=None):
    if drop_chars is None:
        drop_chars = unsafe_chars
    return ''.join([c for c in s if c not in drop_chars])


def safe_string_coerce(s):
    if not isinstance(s, str):
        return s
    return clean_string(s, unsafe_chars + '\n')


def safe_string_multiline_coerce(s):
    if not isinstance(s, str):
        return s
    return clean_string(s, unsafe_chars)
