import jQueryUI from './legacy/lib/jquery-ui-custom.min';
import jQueryUITouchPunch from './legacy/lib/jquery-ui-touch-punch.min';
import { postJSON } from './utils/ajax';
import { notify, notifyError } from './utils/notifications';

const sortEventFactory = (jQuery) => () => {
  const items = jQuery('#sortable_chapters')
    .sortable('toArray', { attribute: 'data-chapter' });
  const data = { chapters: [] };
  // eslint-disable-next-line no-plusplus
  for (let i = 0; i < items.length; i++) {
    data.chapters.push(parseInt(items[i], 10));
  }

  const storyId = window.document.getElementById('sortable_chapters')
    .getAttribute('data-story');
  const url = `/story/${storyId}/sort/`;
  postJSON(url, data)
    .then((response) => response.json())
    .then((result) => {
      if (!result.success) {
        notifyError(data.error);
      } else {
        notify('Главы отсортированы');
      }
    })
    .catch((e) => notifyError(e.toString()));
};

import('jquery').then((module) => {
  const jQuery = module.default;
  jQueryUI(jQuery);
  jQueryUITouchPunch(jQuery);

  // Сортировка глав рассказа
  jQuery('#sortable_chapters').sortable({
    update: sortEventFactory(jQuery),
  });
});
