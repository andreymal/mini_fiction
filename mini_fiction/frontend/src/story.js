import Baz from 'bazooka';
import storyTags from './story_tags/index';

Baz.register({
  storyTags,
});

if (window.document.readyState !== 'loading') {
  Baz.watch();
} else {
  window.document.addEventListener('DOMContentLoaded', () => Baz.watch());
}
