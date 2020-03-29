#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import calendar
from datetime import datetime, timedelta

from flask_babel import pgettext, npgettext

# Django-like timesince instead of timedeltaformat from flask_babel

chunks = (
    (3600 * 24 * 365, '%(num)d year', '%(num)d years'),
    (3600 * 24 * 30, '%(num)d month', '%(num)d months'),
    (3600 * 24 * 7, '%(num)d week', '%(num)d weeks'),
    (3600 * 24, '%(num)d day', '%(num)d days'),
    (3600, '%(num)d hour', '%(num)d hours'),
    (60, '%(num)d minute', '%(num)d minutes'),
)


def timesince(dt=None, now=None, delta=None):
    if delta is None:
        if dt is None:
            return 'N/A'

        if now is None:
            now = datetime.utcnow()
        delta = (now - dt).total_seconds()

        # Разбираемся с високосными днями
        if abs(delta) > 3600:
            leapdays = calendar.leapdays(dt.year, now.year)
            if leapdays != 0:
                if calendar.isleap(dt.year):
                    leapdays -= 1
                elif calendar.isleap(now.year):
                    leapdays += 1
            delta -= timedelta(leapdays).total_seconds()

    if delta >= 0 and delta < 60:
        return pgettext('timesince', 'just now')
    if delta < 0 and delta > -60:
        return pgettext('timesince', 'very soon')

    delta_abs = abs(int(delta))

    # Кусок первый
    result = ''  # deal with pylint
    i = 0
    seconds = 0
    for i, (seconds, singular, plural) in enumerate(chunks):
        count = delta_abs // seconds
        if count != 0:
            result = npgettext('timesince', singular, plural, num=count)
            break

    # Кусок второй через запятую
    if i + 1 < len(chunks):
        seconds2, singular2, plural2 = chunks[i + 1]
        count2 = (delta_abs - (seconds * count)) // seconds2
        if count2 != 0:
            result += pgettext('timesince', ', ')
            result += npgettext('timesince', singular2, plural2, num=count2)

    if delta >= 0:
        return pgettext('timesince', '%(delta)s ago') % {'delta': result}
    return pgettext('timesince', 'in %(delta)s') % {'delta': result}


# Workaround for babel-extract
npgettext('timesince', '%(num)d year', '%(num)d years', num=1)
npgettext('timesince', '%(num)d month', '%(num)d months', num=1)
npgettext('timesince', '%(num)d week', '%(num)d weeks', num=1)
npgettext('timesince', '%(num)d day', '%(num)d days', num=1)
npgettext('timesince', '%(num)d hour', '%(num)d hours', num=1)
npgettext('timesince', '%(num)d minute', '%(num)d minutes', num=1)
