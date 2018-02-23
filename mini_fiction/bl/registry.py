#!/usr/bin/env python3
# -*- coding: utf-8 -*-

_cache = {}
_registry = {}


class Resource(object):
    resource_name = None

    def __init__(self, resource_name):
        self.resource_name = resource_name

    def __get__(self, instance, cls):
        target = instance or cls

        # FIXME: Pony ORM does not support setattr
        # if self.resource_name not in target.__dict__:
        if not _cache.get((target, self.resource_name)):
            func = _registry[self.resource_name](target)
            # setattr(target, self.resource_name, func)
            _cache[(target, self.resource_name)] = func

        # return target.__dict__[self.resource_name]
        if target is cls:
            return _cache[(target, self.resource_name)]
        return _cache.pop((target, self.resource_name))


def register(name, get_func):
    _registry[name] = get_func
