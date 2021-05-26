/* eslint-disable no-restricted-globals,no-console */
/* global self, caches, fetch */

import {
  clearCaches, getCache, NOT_FOUND_IN_CACHE, precache,
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

  const cachedResponsePromise = caches.open(cacheName)
    .then((cache) => cache.match(event.request, { ignoreSearch: true })
      .then((matching) => {
        if (matching) {
          console.log('Found cached', event.request.url, ' and serving from', cacheName);
        }
        return matching || Promise.reject(NOT_FOUND_IN_CACHE);
      }));

  const resp = cachedResponsePromise.catch(
    (err) => {
      if (err.message !== NOT_FOUND_IN_CACHE.message) {
        throw err;
      }
      console.log('Resource', event.request.url, 'not found in', cacheName, 'fetching it');
      return fetch(event.request.clone()).then((response) => {
        caches.open(cacheName).then((cache) => {
          if (response.status < 400) {
            console.log('Caching', event.request.url, 'into', cacheName);
            return cache.put(event.request, response.clone());
          }
          console.log('Got', response.status, 'status for', event.request.url, 'skip caching');
          return Promise.reject(new Error('Upstream error'));
        });
      });
    },
  );

  event.respondWith(resp);
});
