#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

import os
import time
import random
from hashlib import sha256
from datetime import datetime

from flask import current_app

from mini_fiction.bl.utils import BaseBL
from mini_fiction.utils.image import save_image, ImageKind
from mini_fiction.validation import Validator
from mini_fiction.validation.logopics import LOGOPIC, LOGOPIC_FOR_UPDATE
from mini_fiction.utils.misc import call_after_request as later


class LogopicBL(BaseBL):
    def create(self, author, data):
        from mini_fiction.models import AdminLog

        data = Validator(LOGOPIC).validated(data)

        picture = data.pop('picture').stream.read()
        picture_metadata = save_image(kind=ImageKind.LOGOPICS, data=picture, extension='jpg')

        logopic = self.model(
            picture=picture_metadata.relative_path,
            sha256sum=picture_metadata.sha256sum,
            **data
        )
        logopic.flush()

        current_app.cache.delete('logopics')
        AdminLog.bl.create(user=author, obj=logopic, action=AdminLog.ADDITION)
        return logopic

    def update(self, author, data):
        from mini_fiction.models import AdminLog

        data = Validator(LOGOPIC_FOR_UPDATE).validated(data, update=True)
        logopic = self.model

        changed_fields = set()

        for key, value in data.items():
            if key == 'picture':
                if value:
                    picture = value.stream.read()
                    old_path = self.model.picture_path
                    picture_metadata = save_image(kind=ImageKind.LOGOPICS, data=picture, extension='jpg')
                    self.model.picture = picture_metadata.relative_path
                    self.model.sha256sum = picture_metadata.sha256sum
                    changed_fields |= {'picture',}
                    later(lambda: old_path.unlink(missing_ok=True))
            else:
                if key == 'original_link_label':
                    value = value.replace('\r', '')
                if getattr(logopic, key) != value:
                    setattr(logopic, key, value)
                    changed_fields |= {key,}

        if changed_fields:
            logopic.updated_at = datetime.utcnow()
            current_app.cache.delete('logopics')

            AdminLog.bl.create(
                user=author,
                obj=logopic,
                action=AdminLog.CHANGE,
                fields=sorted(changed_fields),
            )

        return logopic

    def delete(self, author):
        from mini_fiction.models import AdminLog
        AdminLog.bl.create(user=author, obj=self.model, action=AdminLog.DELETION)
        old_path = self.model.picture_path
        later(lambda: old_path.unlink(missing_ok=True))
        self.model.delete()
        current_app.cache.delete('logopics')

    def get_all(self):
        result = current_app.cache.get('logopics')
        if result is not None:
            return result

        result = []
        for lp in self.model.select(lambda x: x.visible):
            data = {
                'url': lp.url,
                'original_link': lp.original_link,
                'original_link_label': {'': ''},
            }
            for line in lp.original_link_label.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if 0 <= line.find('=') <= 4:
                    lang, line = line.split('=', 1)
                    data['original_link_label'][lang] = line.strip()
                else:
                    data['original_link_label'][''] = line
            result.append(data)

        current_app.cache.set('logopics', result, 7200)
        return result

    def get_current(self):
        logos = self.get_all()
        if not logos:
            return None
        logo = dict(random.Random(int(time.time()) // 3600).choice(logos))
        return logo
