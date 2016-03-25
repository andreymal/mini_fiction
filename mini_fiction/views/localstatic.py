#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from flask import current_app, send_from_directory


def localstatic(filename):
    return send_from_directory(os.path.abspath(current_app.config['LOCALSTATIC_ROOT']), filename)
