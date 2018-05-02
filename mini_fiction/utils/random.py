#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Обёртка над системным рандомом, безопасная для генерации ключей,
# капчи и прочих важных вещей.

from random import SystemRandom


_sysrand = SystemRandom()


# Для случайных строк по умолчанию используется такой набор символов, который
# без проблем прочтёт человек — не попутает букву O и нолик, например
default_random_chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz123456789'


def choice(seq):
    return _sysrand.choice(seq)


def randrange(start, stop=None, step=1):
    return _sysrand.randrange(start, stop, step)


def random_string(length, chars=None):
    if chars is None:
        chars = default_random_chars
    return ''.join(_sysrand.choice(chars) for _ in range(length))
