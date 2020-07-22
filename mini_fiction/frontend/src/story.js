import 'whatwg-fetch'; // init polyfill for IE11

import Baz from 'bazooka';
import storyTags from './story_tags/index';

/* devblock:start */
require('preact/debug');
/* devblock:end */

Baz.register({
  storyTags,
});

if (window.document.readyState !== 'loading') {
  Baz.watch();
} else {
  window.document.addEventListener('DOMContentLoaded', () => Baz.watch());
}
