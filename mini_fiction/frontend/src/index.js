import Baz from 'bazooka';

import core from './legacy/core';
import common from './legacy/common';
import comments from './legacy/comments';
import bell from './legacy/bell';
import story from './legacy/story';
import editlog from './legacy/editlog';
import captcha from './legacy/captcha';
import lazyBaz from './utils/lazyBaz';

import {
  alert,
  button,
  collapse,
  dropdown,
  modal,
  tab,
  transition,
} from './legacy/lib/bootstrap.min';

/* devblock:start */
require('preact/debug');
/* devblock:end */

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

Baz.register({
  RichEditor: lazyBaz(() => import('./components/RichEditor')),
  SortableChapters: lazyBaz(() => import('./components/SortableChapters')),
  StoriesCarousel: lazyBaz(() => import('./components/StoriesCarousel')),
  StoryTags: lazyBaz(() => import('./components/StoryTags')),
});

const initialize = (jQuery) => {
  core.init(jQuery);
  transition(jQuery);
  modal(jQuery);
  dropdown(jQuery);
  tab(jQuery);
  alert(jQuery);
  button(jQuery);
  collapse(jQuery);
};

if (window.document.readyState !== 'loading') {
  Baz.watch();
  import('jquery').then(({ default: jQuery }) => initialize(jQuery));
} else {
  window.document.addEventListener('DOMContentLoaded', () => {
    Baz.watch();
    import('jquery').then(({ default: jQuery }) => initialize(jQuery));
  });
}
