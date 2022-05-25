import markItUp from '../../legacy/lib/jquery.markitup';
import mySettings from '../../legacy/markitup-settings';

export default (node) => {
  import('jquery').then(({ default: jQuery }) => {
    markItUp(jQuery);
    // Собственно markitup
    jQuery(node).markItUp(mySettings);
  });

  return () => {
    import('jquery').then(({ default: jQuery }) => {
      jQuery(node).markItUpRemove();
    });
  };
};
