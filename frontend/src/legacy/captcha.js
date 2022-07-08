// Объекты кастомных капч, которые требуют дополнительного джаваскрипта
const _captchas = {};
let _lastCaptchaId = 0;

// Параметры reCaptcha
let _reCaptchaLoading = false;  // добавлен ли скрипт рекапчи на страницу
let _reCaptchaReady = false;  // загрузился ли этот скрипт
const _reCaptchaQueue = [];  // очередь капч, ожидающих загрузки скрипта

// Параметры hCaptcha
let _hCaptchaLoading = false;  // добавлен ли скрипт hcaptcha на страницу
let _hCaptchaReady = false;  // загрузился ли этот скрипт
const _hCaptchaQueue = [];  // очередь капч, ожидающих загрузки скрипта


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

class HCaptcha {
  constructor(container) {
    container.innerHTML = '';
    this._container = container;
    this._key = container.getAttribute('data-key');
    this._widgetId = window.hcaptcha.render(container, {sitekey: container.getAttribute('data-key')});
  }

  destroy = () => {
    this._container.parentNode.removeChild(this._container);
    window.hcaptcha.reset(this._widgetId);

    this._container = null;
    this._key = null;
    this._widgetId = null;
  }
}

const insertReCaptchaScript = () => {
  const script = document.createElement('script');
  script.src = 'https://www.google.com/recaptcha/api.js?onload=_reCaptchaReadyEvent&render=explicit';
  script.async = true;
  script.defer = true;
  document.body.appendChild(script);
};

const initReCaptcha = (container) => {
  _captchas[++_lastCaptchaId] = new ReCaptcha(container);
  container.setAttribute('data-id', _lastCaptchaId.toString());
};

const loadReCaptcha = (container) => {
  if (!_reCaptchaLoading) {
    insertReCaptchaScript();
    _reCaptchaLoading = true;
  }
  if (!_reCaptchaReady) {
    _reCaptchaQueue.push(container);
  } else {
    initReCaptcha(container);
  }
}

const insertHCaptchaScript = () => {
  const script = document.createElement('script');
  script.src = 'https://js.hcaptcha.com/1/api.js?onload=_hCaptchaReadyEvent&render=explicit';
  script.async = true;
  script.defer = true;
  document.body.appendChild(script);
};

const initHCaptcha = (container) => {
  _captchas[++_lastCaptchaId] = new HCaptcha(container);
  container.setAttribute('data-id', _lastCaptchaId.toString());
};

const loadHCaptcha = (container) => {
  if (!_hCaptchaLoading) {
    insertHCaptchaScript();
    _hCaptchaLoading = true;
  }
  if (!_hCaptchaReady) {
    _hCaptchaQueue.push(container);
  } else {
    initHCaptcha(container);
  }
}

const getCaptchaNodes = (content) => [...content.getElementsByClassName('js-captcha')];

const load = (content) => {
  getCaptchaNodes(content)
    .filter(({ classList }) => !classList.contains('js-captcha-active'))
    .forEach(captchaNode => {
      if (captchaNode.dataset.captchaType === 'recaptcha') {
        loadReCaptcha(captchaNode);
      } else if (captchaNode.dataset.captchaType === 'hcaptcha') {
        loadHCaptcha(captchaNode);
      } else {
        console.error(`Unknown captcha type: ${captchaNode.dataset.captchaType}`);
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

const hCaptchaReadyEvent = () => {
  _hCaptchaLoading = true;
  _hCaptchaReady = true;
  _hCaptchaQueue.forEach(node => initReCaptcha(node));
  _hCaptchaQueue.length = 0;
};
window._hCaptchaReadyEvent = hCaptchaReadyEvent;

export default {
  load,
  unload,
}
