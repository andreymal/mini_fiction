import arrowLeft from './images/arrow-left.png';
import arrowRight from './images/arrow-right.png';

const slides = window.document.getElementById('slides');

const settings = {
  width: 524,
  height: 200,
  navigation: {
    active: true,
    effect: 'fade',
  },
  pagination: {
    active: false,
  },
  effect: {
    slide: {
      speed: 1500,
    },
    fade: {
      speed: 300,
      crossfade: false,
    },
  },
  play: {
    active: false,
    effect: 'fade',
    interval: 7500,
    auto: true,
    swap: true,
    pauseOnHover: true,
    restartDelay: 3500,
  },
};

if (slides) {
  Promise
    .all([import('jquery'), import('./legacy/lib/jquery.slides.3.0.4.min')])
    .then(([{ default: jQuery }, { default: jQuerySlides }]) => {
      jQuerySlides(jQuery, window, window.document);
      jQuery(slides).slidesjs(settings);
      jQuery('#slides .slidesjs-previous').html(`<img src="${arrowLeft}"/>`);
      jQuery('#slides .slidesjs-next').html(`<img src="${arrowRight}"/>`);
      slides.classList.remove('carousel-inactive');
    });
}
