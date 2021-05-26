/* eslint-disable no-restricted-globals */
/* global self */

import {
  clearCaches,
  getCache,
  handleResponse,
  precache,
} from './caching';

import { log } from '../utils/logging';

self.addEventListener('install', (event) => event.waitUntil(precache()));

self.addEventListener('activate', (event) => event.waitUntil(clearCaches()));

self.addEventListener('fetch', (event) => {
  const cacheName = getCache(event.request.url);
  const isCacheable = cacheName !== null;
  if (!isCacheable) {
    log('Resource at', event.request.url, 'is not cacheable, skipping');
    return;
  }
  event.respondWith(handleResponse(event, cacheName));
});
