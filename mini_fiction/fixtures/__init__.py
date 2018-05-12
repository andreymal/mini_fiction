#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json

from mini_fiction import dumpload


fixtures_dir = os.path.abspath(os.path.dirname(__file__))


def seed(verbosity=1, only_create=True):
    dumpload.loaddb_console(
        [fixtures_dir],
        verbosity=verbosity,
        only_create=only_create,
    )
