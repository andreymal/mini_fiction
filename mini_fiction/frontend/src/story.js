import Baz from 'bazooka';
import storyTags from './story_tags/index';

Baz.register({
  storyTags,
});

// eslint-disable-next-line no-undef
document.addEventListener('DOMContentLoaded', () => {
  Baz.refresh();
});
