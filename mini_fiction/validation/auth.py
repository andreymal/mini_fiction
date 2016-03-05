#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.validation import common
from mini_fiction.validation.utils import required


REGISTRATION = {
    'username': required(common.USERNAME),
    'password': required(common.PASSWORD),
    'email': required(common.EMAIL),
}


LOGIN = {
    # not common.*, because old usernames and passwords can be invalid
    'username': {'type': 'string', 'required': True, 'maxlength': 128},
    'password': {'type': 'string', 'required': True, 'maxlength': 128},
}
