/* eslint-disable no-console */
/* global IS_DEV */

export const log = (...args) => {
  if (IS_DEV) {
    console.log(...args);
  }
};

export const error = (...args) => {
  console.error(...args);
};
