#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json

from mini_fiction import dumpload


fixtures_dir = os.path.abspath(os.path.dirname(__file__))


def seed(progress=True):
    dumpload.loaddb_console([fixtures_dir], progress=progress)
