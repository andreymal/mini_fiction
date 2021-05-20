import jQueryUI from './legacy/lib/jquery-ui-custom.min';
import jQueryUITouchPunch from './legacy/lib/jquery-ui-touch-punch.min';
import core from './legacy/core';

const sortEventFactory = (jQuery) => () => {
  const items = jQuery('#sortable_chapters').sortable('toArray', { attribute: 'data-chapter' });
  const data = { chapters: [] };
  // eslint-disable-next-line no-plusplus
  for (let i = 0; i < items.length; i++) {
    data.chapters.push(parseInt(items[i], 10));
  }

  const url = `/story/${window.document.getElementById('sortable_chapters')
    .getAttribute('data-story')}/sort/`;
  core.ajax.postJSON(url, data)
    .then((response) => response.json())
    .then((response) => {
      core.handleResponse(response, url);
    })
    .catch(core.handleError);
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
