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
from mini_fiction.validation import Validator
from mini_fiction.validation.logopics import LOGOPIC, LOGOPIC_FOR_UPDATE


class LogopicBL(BaseBL):
    def create(self, author, data):
        from mini_fiction.models import AdminLog

        data = Validator(LOGOPIC).validated(data)

        picture = data.pop('picture')
        logopic = self.model(picture='pending', sha256sum='pending', **data)
        logopic.flush()
        logopic.bl.set_picture_data(picture)
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
                    self.set_picture_data(value)
                    changed_fields |= {'picture',}
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
        self.model.delete()
        current_app.cache.delete('logopics')

    def set_picture_data(self, f):
        pathset = ('logopics', str(self.model.id), f.filename)
        urlpath = '/'.join(pathset)  # equivalent to ospath except Windows!
        ospath = os.path.join(current_app.config['MEDIA_ROOT'], *pathset)

        dirpath = os.path.dirname(ospath)
        if not os.path.isdir(dirpath):
            os.makedirs(dirpath)

        if self.model.picture:
            old_ospath = os.path.join(current_app.config['MEDIA_ROOT'], self.model.picture)
            if os.path.isfile(old_ospath):
                os.remove(old_ospath)

        f.save(ospath)

        h = sha256(b'')
        with open(ospath, 'rb') as fp:
            while True:
                data = fp.read(16384)
                if not data:
                    break
                h.update(data)

        self.model.picture = urlpath
        self.model.sha256sum = h.hexdigest()
        return urlpath

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
