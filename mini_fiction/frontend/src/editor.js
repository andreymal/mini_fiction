import markItUp from './legacy/lib/jquery.markitup';
import mySettings from './legacy/markitup-settings';

import('jquery').then(({ default: jQuery }) => {
  markItUp(jQuery);
  // Собственно markitup
  jQuery('.with-markitup').markItUp(mySettings);
});
