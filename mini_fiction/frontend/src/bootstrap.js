import {
  alert,
  button,
  collapse,
  dropdown,
  modal,
  tab,
  transition,
} from './legacy/lib/bootstrap.min';

import('jquery').then(({ default: jQuery }) => {
  transition(jQuery);
  modal(jQuery);
  dropdown(jQuery);
  tab(jQuery);
  alert(jQuery);
  button(jQuery);
  collapse(jQuery);
});
