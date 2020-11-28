#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

import pytz
import babel.dates
from flask_babel import get_locale, gettext, lazy_pgettext


deprecated_timezones = {
    'Canada/Atlantic',
    'Canada/Central',
    'Canada/Eastern',
    'Canada/Mountain',
    'Canada/Newfoundland',
    'Canada/Pacific',
    'US/Alaska',
    'US/Arizona',
    'US/Central',
    'US/Eastern',
    'US/Hawaii',
    'US/Mountain',
    'US/Pacific',
    'GMT',
}

pgettext = lazy_pgettext  # avoid pybabel extract problem

tz_category_names = {
    'Africa': pgettext('tz_category', 'Africa'),
    'America': pgettext('tz_category', 'America'),
    'Antarctica': pgettext('tz_category', 'Antarctica'),
    'Arctic': pgettext('tz_category', 'Arctic'),
    'Asia': pgettext('tz_category', 'Asia'),
    'Atlantic': pgettext('tz_category', 'Atlantic'),
    'Australia': pgettext('tz_category', 'Australia'),
    'Europe': pgettext('tz_category', 'Europe'),
    'Indian': pgettext('tz_category', 'Indian'),
    'Pacific': pgettext('tz_category', 'Pacific'),
    'UTC': pgettext('tz_category', 'UTC'),
}


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


def get_timezone_info(tzname, dt=None, locale=None):
    """Возвращает читабельную информацию о часовом поясе, а также смещение
    для удобной сортировки."""

    if locale is None:
        locale = get_locale()

    if dt is None:
        dt = datetime.utcnow().replace(tzinfo=pytz.UTC)

    # Расчёт смещения часового пояса по состоянию на сегодня
    tz = pytz.timezone(tzname)
    tz_dt = tz.normalize(dt)
    offset = tz_dt.tzinfo.utcoffset(tz_dt)
    assert offset is not None
    hours, seconds = divmod(int(offset.total_seconds()), 3600)
    offset_str = '{:+03d}:{:02d}'.format(
        hours,
        seconds // 60,
    )

    tz_category = tzname.split('/', 1)[0]
    tz_category_name = str(tz_category_names.get(tz_category, tz_category))
    tz_human_name = babel.dates.get_timezone_location(tzname, locale=locale, return_city=True)

    return (
        tzname,
        tz_category_name,
        tz_human_name,
        int(offset.total_seconds()),
        offset_str,
    )


def get_timezone_infos(locale=None):
    """Возвращает список с читабельной информацией о часовых поясах,
    отсортированный по смещению.
    """

    if locale is None:
        locale = get_locale()

    result = []

    dt = datetime.utcnow().replace(tzinfo=pytz.UTC)

    for tzname in pytz.common_timezones:
        if tzname in deprecated_timezones:
            continue
        result.append(get_timezone_info(tzname, dt=dt, locale=locale))

    result.sort(key=lambda x: (x[3], x[0]))
    return result
