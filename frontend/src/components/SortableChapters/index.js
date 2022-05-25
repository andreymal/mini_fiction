import jQueryUI from '../../legacy/lib/jquery-ui-custom.min';
import jQueryUITouchPunch from '../../legacy/lib/jquery-ui-touch-punch.min';
import { postJSON } from '../../utils/ajax';
import { notify, notifyError } from '../../utils/notifications';

const sortEventFactory = (jQuery) => (node) => () => {
  const items = jQuery(node)
    .sortable('toArray', { attribute: 'data-chapter' });
  const data = { chapters: [] };
  // eslint-disable-next-line no-plusplus
  for (let i = 0; i < items.length; i++) {
    data.chapters.push(parseInt(items[i], 10));
  }

  const storyId = node.getAttribute('data-story');
  const url = `/story/${storyId}/sort/`;
  postJSON(url, data)
    .then((response) => response.json())
    .then((result) => {
      if (!result.success) {
        notifyError(result.error);
      } else {
        notify('Главы отсортированы');
      }
    })
    .catch((e) => notifyError(e.toString()));
};

export default (node) => {
  import('jquery').then(({ default: jQuery }) => {
    jQueryUI(jQuery);
    jQueryUITouchPunch(jQuery);

    // Сортировка глав рассказа
    jQuery(node).sortable({
      update: sortEventFactory(jQuery)(node),
    });
  });

  return () => {
    import('jquery').then(({ default: jQuery }) => {
      jQuery(node).sortable('disable');
    });
  };
};
