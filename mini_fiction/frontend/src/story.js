import Baz from 'bazooka';
import storyTags from './story_tags/index';
// eslint-disable-next-line
import storyStyles from './story_tags/styles.styl';


Baz.register({
  storyTags,
});

// eslint-disable-next-line no-undef
document.addEventListener('DOMContentLoaded', () => {
  Baz.refresh();
});
