'use strict';

/* global core: false, grecaptcha: false */


var captcha = {
    // Объекты кастомных капч, которые требуют дополнительного джаваскрипта
    _captchas: {},
    _lastCaptchaId: 0,

    // Параметры reCaptcha
    _reCaptchaLoading: false,  // добавлен ли скрипт рекапчи на страницу
    _reCaptchaReady: false,  // загрузился ли этот скрипт
    _reCaptchaQueue: [],  // очередь капч, ожидающих загрузки скрипта

    load: function(content) {
        var captchas = content.getElementsByClassName('js-recaptcha');
        for (var i = 0; i < captchas.length; i++) {
            var captchaNode = captchas[i];
            if (captchaNode.classList.contains('js-recaptcha-active')) {
                continue;
            }

            if (!this._reCaptchaLoading) {
                var script = document.createElement('script');
                script.src = 'https://www.google.com/recaptcha/api.js?onload=_reCaptchaReadyEvent&render=explicit';
                script.async = true;
                script.defer = true;
                document.body.appendChild(script);
                this._reCaptchaLoading = true;
            }

            if (!this._reCaptchaReady) {
                this._reCaptchaQueue.push(captchaNode);
            } else {
                this.initReCaptcha(captchaNode);
            }
        }
    },

    initReCaptcha: function(container) {
        var captchaObj = new captcha.ReCaptcha(container);
        this._captchas[++this._lastCaptchaId] = captchaObj;
        container.setAttribute('data-id', this._lastCaptchaId.toString());
    },

    unload: function(content) {
        this._reCaptchaQueue = [];

        var captchas = content.getElementsByClassName('js-recaptcha');
        for (var i = 0; i < captchas.length; i++) {
            var captchaNode = captchas[i];
            if (! captchaNode.hasAttribute('data-id')) {
                continue;
            }

            var cid = captchaNode.getAttribute('data-id');
            var captchaObj = this._captchas[cid];
            delete this._captchas[cid];
            captchaObj.destroy();
            captchaObj = null;
        }
    },

    _reCaptchaReadyEvent: function() {
        this._reCaptchaLoading = true;
        this._reCaptchaReady = true;

        var queue = this._reCaptchaQueue;
        this._reCaptchaQueue = [];

        for (var i = 0; i < queue.length; i++) {
            this.initReCaptcha(queue[i]);
        }
    },
};


captcha.ReCaptcha = function(container) {
    container.innerHTML = '';
    this._container = container;
    this._key = container.getAttribute('data-key');
    this._widgetId = window.grecaptcha.render(container, {sitekey: container.getAttribute('data-key')});
};


captcha.ReCaptcha.prototype.destroy = function() {
    this._container.parentNode.removeChild(this._container);
    window.grecaptcha.reset(this._widgetId);

    this._container = null;
    this._key = null;
    this._widgetId = null;
};


core.onload(captcha.load.bind(captcha));
core.onunload(captcha.unload.bind(captcha));

// рекапча отказывается принимать точку в onload
window._reCaptchaReadyEvent = captcha._reCaptchaReadyEvent.bind(captcha);
