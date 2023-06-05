#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name,unused-variable

from flask import url_for


def test_data_stub(app, client):
    res = client.get(url_for('index.index'))
    assert 'Здесь пока ничего нет'.encode('utf-8') in res.data
