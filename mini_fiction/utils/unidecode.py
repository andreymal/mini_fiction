#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unidecode import unidecode  # pylint: disable=unused-import


def _monkey_patch():
    from unidecode import x004
    data = dict((chr(i + 0x400), x) for i, x in enumerate(x004.data))

    data.update({
        'й': 'y',
        'ю': 'y',
        'я': 'ya',
        'ё': 'yo',
        'Й': 'Y',
        'Ю': 'Y',
        'Я': 'Ya',
        'Ё': 'Yo',
    })

    x004.data = tuple(x for _, x in sorted(data.items()))

_monkey_patch()
