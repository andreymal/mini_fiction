#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Собираем список сомнительных символов, чтобы вычищать их при валидации,
# ибо нефиг. \r попутно тоже вычищаем за ненадобностью, \n и \t оставляем
unsafe_chars = [chr(x) for x in range(32) if x not in (9, 10,)]
unsafe_chars += [chr(x) for x in range(127, 160)]
unsafe_chars += ['\ufffe', '\ufeff', '\uffff']
unsafe_chars = ''.join(unsafe_chars)


def merge(src, target):
    result = src.copy()
    result.update(target)
    return result


def required(src):
    result = src.copy()
    result['required'] = True
    return result


def optional(src):
    result = src.copy()
    result['required'] = False
    return result


def bool_coerce(v):
    if v in (True, 1, '1', 'y', 'Y', 'on', 'true'):
        return True
    if v in (False, 0, '0', 'n', 'N', 'off', 'false', ''):
        return False
    raise ValueError


def clean_string(s, chars):
    return ''.join([c for c in s if c not in chars])


def safe_string_coerce(s):
    if not isinstance(s, str):
        return s
    return clean_string(s, unsafe_chars + '\n')


def safe_string_multiline_coerce(s):
    if not isinstance(s, str):
        return s
    return clean_string(s, unsafe_chars)


def strip_string_coerce(s):
    if not isinstance(s, str):
        return s
    return s.strip()
