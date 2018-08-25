// Объекты кастомных капч, которые требуют дополнительного джаваскрипта
const _captchas = {};
let _lastCaptchaId = 0;

// Параметры reCaptcha
let _reCaptchaLoading = false;  // добавлен ли скрипт рекапчи на страницу
let _reCaptchaReady = false;  // загрузился ли этот скрипт
const _reCaptchaQueue = [];  // очередь капч, ожидающих загрузки скрипта


class ReCaptcha {
  constructor(container) {
    container.innerHTML = '';
    this._container = container;
    this._key = container.getAttribute('data-key');
    this._widgetId = window.grecaptcha.render(container, {sitekey: container.getAttribute('data-key')});
  }

  destroy = () => {
    this._container.parentNode.removeChild(this._container);
    window.grecaptcha.reset(this._widgetId);

    this._container = null;
    this._key = null;
    this._widgetId = null;
  }
}

const initReCaptcha = (container) => {
  _captchas[++_lastCaptchaId] = new ReCaptcha(container);
  container.setAttribute('data-id', _lastCaptchaId.toString());
};

const getCaptchaNodes = (content) => [...content.getElementsByClassName('js-recaptcha')];

const insertReCaptchaScript = () => {
  const script = document.createElement('script');
  script.src = 'https://www.google.com/recaptcha/api.js?onload=_reCaptchaReadyEvent&render=explicit';
  script.async = true;
  script.defer = true;
  document.body.appendChild(script);
};

const load = (content) => {
  getCaptchaNodes(content)
    .filter(({ classList }) => !classList.contains('js-recaptcha-active'))
    .forEach(captchaNode => {
      if (!_reCaptchaLoading) {
        insertReCaptchaScript();
        _reCaptchaLoading = true;
      }
      if (!_reCaptchaReady) {
        _reCaptchaQueue.push(captchaNode);
      } else {
        initReCaptcha(captchaNode);
      }
    });
};

const unload = (content) => {
  _reCaptchaQueue.length = 0;
  getCaptchaNodes(content)
    .filter(node => node.hasAttribute('data-id'))
    .forEach(({ dataset: { id }}) => {
      const captchaObj = _captchas[id];
      delete _captchas[id];
      captchaObj.destroy();
    });
};

const reCaptchaReadyEvent = () => {
  _reCaptchaLoading = true;
  _reCaptchaReady = true;
  _reCaptchaQueue.forEach(node => initReCaptcha(node));
  _reCaptchaQueue.length = 0;
};
window._reCaptchaReadyEvent = reCaptchaReadyEvent;

export default {
  load,
  unload,
}
