import 'whatwg-fetch'; // init polyfill for IE11

import core from './legacy/core';
import common from './legacy/common';
import comments from './legacy/comments';
import bell from './legacy/bell';
import story from './legacy/story';
import editlog from './legacy/editlog';
import captcha from './legacy/captcha';


const { document } = window;

core.oninit(common.init.bind(common));
core.onload(common.load.bind(common));
core.onunload(common.unload.bind(common));
core.onloadModal(common.loadModal.bind(common));
core.onunloadModal(common.unloadModal.bind(common));

core.onload(bell.load.bind(bell));

core.oninit(story.init.bind(story));
core.onload(story.load.bind(story));
core.onunload(story.unload.bind(story));

core.onload(editlog.load.bind(editlog));
core.onloadModal(editlog.loadModal.bind(editlog));

core.onload(captcha.load);
core.onunload(captcha.unload);

core.onload(comments.load.bind(comments));
core.onunload(comments.unload.bind(comments));

if (window.document.readyState !== 'loading') {
  core.init();
} else {
  window.document.addEventListener('DOMContentLoaded', () => core.init());
}
