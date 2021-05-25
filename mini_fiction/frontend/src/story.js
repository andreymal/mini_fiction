import Baz from 'bazooka';
import storyTags from './story_tags/index';
import SortableChapters from './components/SortableChapters/index';

/* devblock:start */
require('preact/debug');
/* devblock:end */

Baz.register({
  storyTags,
  SortableChapters,
});

if (window.document.readyState !== 'loading') {
  Baz.watch();
} else {
  window.document.addEventListener('DOMContentLoaded', () => Baz.watch());
}
