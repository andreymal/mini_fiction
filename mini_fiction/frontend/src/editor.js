import markItUp from './legacy/lib/jquery.markitup';
import mySettings from './legacy/markitup-settings';

import('jquery').then((module) => {
  const jQuery = module.default;
  markItUp(jQuery);
  // Собственно markitup
  jQuery('.with-markitup').markItUp(mySettings);
});
