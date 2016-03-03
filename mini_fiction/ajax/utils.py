#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import wraps

from flask import request, jsonify
from flask_login import current_user


def ajax_login_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Необходимо авторизоваться!', 'success': False}), 401
        return f(*args, **kwargs)
    return decorator
