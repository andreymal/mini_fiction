import Baz from 'bazooka';
import storyTags from './story_tags/index';
import SortableChapters from './components/SortableChapters/index';
import RichEditor from './components/RichEditor/index';

/* devblock:start */
require('preact/debug');
/* devblock:end */

Baz.register({
  storyTags,
  SortableChapters,
  RichEditor,
});

Baz.watch();
