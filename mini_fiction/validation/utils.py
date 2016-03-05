#!/usr/bin/env python3
# -*- coding: utf-8 -*-


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
    if v in (True, 1, '1', 'y', 'Y', 'on'):
        return True
    if v in (False, 0, '0', 'n', 'N', 'off', ''):
        return False
    raise ValueError
