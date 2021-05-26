/* eslint-disable no-restricted-globals,no-console */
/* global caches, fetch, STATIC_PATH */

import { log } from '../utils/logging';

const CURRENT_CACHES = {
  static: 'static-v1',
  common: 'common-v1',
};

const COMMON_ASSETS = new RegExp('/media/(avatars|characters|logopics)/');

const MANIFEST = '/manifest.json';

/**
 * Precache application assets (js/css)
 * @returns {Promise<void>}
 */
export const precache = async () => {
  const rawManifest = await fetch(MANIFEST);
  const manifest = await rawManifest.json();
  const resources = Object.values(manifest)
    .map((asset) => asset.src)
    .filter((src) => !src.endsWith('.map'))
    .map((src) => `${STATIC_PATH}${src}`);
  log('Going to cache', resources.length, 'resources:', resources);
  caches.open(CURRENT_CACHES.static)
    .then((cache) => cache.addAll(resources));
};

/**
 * Delete all caches that aren't named in CURRENT_CACHES
 * @returns {Promise<void>}
 */
export const clearCaches = async () => {
  const expectedCacheNamesSet = new Set(Object.values(CURRENT_CACHES));
  caches.keys()
    .then((cacheNames) => Promise.all(
      cacheNames.map((cacheName) => {
        if (!expectedCacheNamesSet.has(cacheName)) {
          log('Deleting out of date cache:', cacheName);
          return caches.delete(cacheName);
        }
        return Promise.resolve();
      }),
    ));
};

/**
 * Infer cache for resource
 * @param {string} url
 * @returns {string|null}
 */
export const getCache = (url) => {
  const pathName = new URL(url).pathname;
  if (pathName.startsWith(STATIC_PATH)) {
    return CURRENT_CACHES.static;
  }
  if (COMMON_ASSETS.test(pathName)) {
    return CURRENT_CACHES.common;
  }
  return null;
};

/**
 * Handle cacheable request
 * @param {FetchEvent} event
 * @param {string} cacheName
 * @returns Promise<Response>
 */
export const handleResponse = async (event, cacheName) => {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(event.request, { ignoreSearch: true });
  if (cachedResponse) {
    log('Found cached', event.request.url, 'and serving from', cacheName);
    return cachedResponse;
  }
  log('Resource', event.request.url, 'not found in', cacheName, 'fetching it');
  const freshResponse = await fetch(event.request.clone());
  if (freshResponse.status < 400) {
    log('Caching', event.request.url, 'into', cacheName);
    await cache.put(event.request, freshResponse.clone());
  }
  return freshResponse;
};
