#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json

from mini_fiction import models


fixtures_dir = os.path.abspath(os.path.dirname(__file__))


def seed():
    for f in sorted(os.listdir(fixtures_dir)):
        if not f.lower().endswith('.json'):
            continue
        with open(os.path.join(fixtures_dir, f), 'rb') as fp:
            items = json.loads(fp.read().decode('utf-8-sig'))
        for x in items:
            seed_item(x)


def seed_item(item):
    kwargs = dict(item.get('fields', {}))
    # TODO: composite primary keys
    if 'pk' in item:
        obj = getattr(models, item['model']).get(id=item['pk'])
        if obj:
            print('Exists', item['model'], obj.id)
            return False
        kwargs['id'] = item['pk']
    obj = getattr(models, item['model'])(**kwargs)
    obj.flush()
    print('Created', item['model'], obj.id)
    return True
