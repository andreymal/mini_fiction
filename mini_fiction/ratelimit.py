#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

import redis


class RateLimitExceeded(Exception):
    def __init__(self, message, limit_name=None, count=None, target=None, ttl=None):
        super().__init__(message)
        self.limit_name = limit_name
        self.count = count
        self.target = target
        self.ttl = ttl

    def summary(self) -> str:
        return 'limit_name={} target={} count={} ttl={}'.format(
            self.limit_name, self.target, self.count, self.ttl
        )


class BaseRateLimiter:
    def __init__(self, app):
        self._limits = app.config['RATE_LIMITS']

    # low-level api

    def get_key(self, key):
        raise NotImplementedError

    def incr_key(self, key, timeout):
        raise NotImplementedError

    def get_key_ttl(self, key):
        raise NotImplementedError

    # mid-level api

    def check_key(self, key, max_count, interval, incr=True):
        # first check without increment
        count = self.get_key(key)
        if max_count >= 0 and count >= max_count:
            return False, count

        # then increment and check again to prevent race condition
        if incr:
            count = self.incr_key(key, timeout=interval)
            if max_count >= 0 and count > max_count:
                return False, count

        return True, count

    def make_key(self, limit_name, target, interval):
        i = int(time.time() / interval)
        return '{}_{}_{}'.format(limit_name, target, i)

    # high-level api

    def limit(self, limit_name, target, incr=True):
        try:
            max_count, interval = self._limits[limit_name]
        except KeyError:
            raise KeyError('Unknown rate limit {!r}'.format(limit_name))

        key = self.make_key(limit_name, target, interval)
        success, count = self.check_key(key, max_count, interval, incr=incr)
        if not success:
            raise RateLimitExceeded("Rate limit exceeded", limit_name, count, target, ttl=self.get_key_ttl(key))
        return count

    def get_limit_ttl(self, limit_name, target):
        try:
            _, interval = self._limits[limit_name]
        except KeyError:
            raise KeyError('Unknown rate limit {!r}'.format(limit_name))

        key = self.make_key(limit_name, target, interval)
        return self.get_key_ttl(key)


class NullRateLimiter(BaseRateLimiter):
    def get_key(self, key):
        return 0

    def incr_key(self, key, timeout):
        return 0

    def get_key_ttl(self, key):
        return 0


class RedisRateLimiter(BaseRateLimiter):
    def __init__(self, app):
        super().__init__(app)
        self._redis = redis.Redis(**app.config['RATE_LIMIT_BACKEND'])
        self._prefix = app.config.get('RATE_LIMIT_PREFIX') or ''

    def get_key(self, key):
        count = self._redis.get(self._prefix + key)
        if count:
            return int(count.decode('ascii'))
        return 0

    def incr_key(self, key, timeout):
        count = self._redis.incr(self._prefix + key)
        if count == 1:
            self._redis.expire(self._prefix + key, timeout)
        return count

    def get_key_ttl(self, key):
        return max(0, self._redis.ttl(self._prefix + key))
