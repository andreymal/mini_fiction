#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import select, count

from mini_fiction.models import AbuseReport
from mini_fiction.templatetags import registry


@registry.simple_tag()
def unread_abuse_reports_count():
    return select(
        (x.target_type, x.target_id, count(x.id))
        for x in AbuseReport
        if not x.ignored and x.resolved_at is None
    ).count()
