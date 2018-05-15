#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from base64 import b64decode, b64encode

from werkzeug.security import safe_str_cmp


def pbkdf2_encode(password, salt=None, iterations=100000):
    from hashlib import pbkdf2_hmac
    if not salt:
        salt = b64encode(os.urandom(32)).decode('ascii').strip()
    else:
        assert '$' not in salt

    result = pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=iterations,
        dklen=None,
    )

    result = b64encode(result).decode('ascii').strip()
    return "pbkdf2_sha256${0}${1}${2}".format(iterations, salt, result)


def pbkdf2_check(data, password):
    try:
        algorithm, iterations, salt, _ = data.split('$', 3)
        iterations = int(iterations)
    except Exception:
        raise ValueError('Invalid hash format')
    if algorithm != 'pbkdf2_sha256':
        raise ValueError('Unknown pbkdf2 algorithm variant')

    data2 = pbkdf2_encode(password, salt, iterations)
    return safe_str_cmp(data, data2)


def bcrypt_encode(password, bcrypt_salt=None):
    import bcrypt
    if not bcrypt_salt:
        bcrypt_salt = bcrypt.gensalt()
    else:
        assert '$' in bcrypt_salt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt_salt).decode('utf-8', 'ascii')


def bcrypt_check(data, password):
    import bcrypt
    try:
        encoded = data.encode('utf-8')
        encoded2 = bcrypt.hashpw(password.encode('utf-8'), encoded)
    except Exception:
        raise ValueError('Invalid hash format')
    return safe_str_cmp(encoded, encoded2)


def _scrypt_password_hash(password, salt, Nexp=14, r=8, p=1, keylen=64):
    import scrypt
    h = scrypt.hash(
        password.encode('utf-8'),
        b64decode(salt),
        2 << Nexp, r, p, keylen
    )
    return b64encode(h).decode('ascii').strip()


def scrypt_encode(password, salt=None):
    if not salt:
        salt = b64encode(os.urandom(32)).decode('ascii').strip()
    else:
        assert '$' not in salt
    args = {'salt': salt, 'Nexp': 14, 'r': 8, 'p': 1, 'keylen': 64}
    h = _scrypt_password_hash(password, **args)
    return '{salt}${Nexp}${r}${p}${keylen}${h}'.format(h=h, **args)


def scrypt_check(data, password):
    try:
        salt, Nexp, r, p, keylen, h = data.split('$')
        Nexp = int(Nexp, 10)
        r = int(r, 10)
        p = int(p, 10)
        keylen = int(keylen, 10)
    except Exception:
        raise ValueError('Invalid hash format')
    return safe_str_cmp(h, _scrypt_password_hash(password, salt, Nexp, r, p, keylen))
