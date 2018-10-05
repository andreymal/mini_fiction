#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytz


def parse_tzinfo(tzinfo=None):
    if not tzinfo:
        return pytz.timezone('UTC')

    if isinstance(tzinfo, str):
        return pytz.timezone(tzinfo)

    if not isinstance(tzinfo, pytz.BaseTzInfo):
        raise TypeError

    return tzinfo


def apply_tzinfo(tm, tzinfo=None):
    """Применяет часовой пояс ко времени, перематывая время на нужное число
    часов/минут.

    Если у переданного в функцию времени нет часового пояса, он считается UTC.
    Аргумент tzinfo может быть строкой с названием часового пояса;
    None считается за UTC.
    """

    tzinfo = parse_tzinfo(tzinfo)

    if not tm.tzinfo:
        tm = tzinfo.fromutc(tm)
    elif tm.tzinfo != tzinfo:
        tm = tzinfo.normalize(tm)
    return tm


def set_tzinfo(tm, tzinfo=None, is_dst=False):
    """Прикрепляет часовой пояс к объекту datetime, который без пояса.
    Возвращает объект datetime с прикреплённым часовым поясом, но значения
    (в частности, день и час), остаются теми же, что и были.
    Для перевода времени из одного часового пояса в другой см. apply_tzinfo.
    Аргумент tzinfo может быть строкой с названием часового пояса;
    None считется за UTC.

    :param datetime tm: время (без часового пояса)
    :param tzinfo: часовой пояс, который надо прикрепить
    :param bool is_dst: в случае неоднозначностей (например,
      31 октября 2010-го 02:00 - 02:59 по Москве) указывает, считать это время
      летним (True) или зимним (False)
    :rtype: datetime
    """

    if tm.tzinfo:
        raise ValueError('datetime already has tzinfo')

    tzinfo = parse_tzinfo(tzinfo)
    return tzinfo.localize(tm, is_dst=is_dst)
