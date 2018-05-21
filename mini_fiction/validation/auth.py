#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.validation import common
from mini_fiction.validation.utils import uniondict


REGISTRATION = {
    'username': uniondict(common.USERNAME, {'required': True}),
    'password': uniondict(common.PASSWORD, {'required': True}),
    'email': uniondict(common.EMAIL, {'required': True}),
}


LOGIN = {
    # not common.*, because old usernames and passwords can be invalid
    'username': {'type': 'string', 'required': True, 'maxlength': 128},
    'password': {'type': 'string', 'required': True, 'maxlength': 128},
}
