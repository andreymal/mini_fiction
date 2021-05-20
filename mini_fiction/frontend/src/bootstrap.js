import {
  affix,
  alert,
  button,
  carousel,
  collapse,
  dropdown,
  modal,
  popover,
  scrollspy,
  tab,
  tooltip,
  transition,
  typeahead,
} from './legacy/lib/bootstrap.min';

import('jquery').then((module) => {
  const jQuery = module.default;
  transition(jQuery);
  modal(jQuery);
  dropdown(jQuery);
  scrollspy(jQuery);
  tab(jQuery);
  tooltip(jQuery);
  popover(jQuery);
  affix(jQuery);
  alert(jQuery);
  button(jQuery);
  collapse(jQuery);
  carousel(jQuery);
  typeahead(jQuery);
});
