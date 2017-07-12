'use strict';


var core = {
    csrftoken: null,
    nav: null,
    content: null,

    modalShow: false,
    modalClosing: false,
    modalElement: null,
    modalBackgr: null,
    loadingIcon: null,
    notifications: null,

    initCallbacks: [],
    loadCallbacks: [],
    unloadCallbacks: [],
    loadModalCallbacks: [],
    unloadModalCallbacks: [],

    started: false,

    /*
     * Инициализация всего этого дела
     */
    init: function() {
        if (this.started) {
            return;
        }
        this.started = true;

        // Это вызывается напрямую из других модулей при ошибках fetch
        this.handleError = this.__handleError.bind(this);

        this.nav = document.getElementById('nav-main');
        this.content = document.getElementById('content');
        this.modalElement = document.getElementById('modal');
        this.modalBackgr = document.getElementById('modal-bg');
        this.modalBackgr.addEventListener('click', this._modalHideEvent.bind(this));
        this.loadingIcon = document.getElementById('loading-icon');
        this.notifications = document.getElementById('popup-notifications');

        var i;

        for (i = 0; i < this.initCallbacks.length; i++) {
            this.initCallbacks[i]();
        }
        this.initCallbacks = null;

        // Включение навигации через ajax
        this.ajaxify();

        // Показываем предустановленное модальное окно
        if (this.modalElement.childNodes.length > 0) {
            this.modal(null, true, true);
        }

        // Имитируем событие загрузки страницы, чтобы другие модули обработали страницу
        var isModal = window.amajaxify && window.amajaxify.isModalNow();
        var content = isModal ? this.modalElement : this.content;
        for (i = 0; i < this.loadCallbacks.length; i++) {
            this.loadCallbacks[i](content, isModal);
        }
    },

    oninit: function(callback, noautostart) {
        if (this.started) {
            if (!noautostart) {
                callback();
            }
            return;
        }
        this.initCallbacks.push(callback);
    },

    onload: function(callback, noautostart) {
        this.loadCallbacks.push(callback);
        if (this.started && !noautostart) {
            var isModal = window.amajaxify && window.amajaxify.isModalNow();
            var content = isModal ? this.modalElement : this.content;
            callback(content, isModal);
        }
    },

    onunload: function(callback) {
        this.unloadCallbacks.push(callback);
    },

    onloadModal: function(callback) {
        this.loadModalCallbacks.push(callback);
    },

    onunloadModal: function(callback) {
        this.unloadModalCallbacks.push(callback);
    },

    /** Показывает уведомление с переданным текстом */
    notify: function(text) {
        var not = document.createElement('div');
        not.textContent = text;
        this.putNotification(not);
    },

    /** Показывает уведомление-ошибку с переданным текстом */
    notifyError: function(text) {
        var not = document.createElement('div');
        not.classList.add('notice-error');
        not.textContent = text;
        this.putNotification(not);
    },

    /** Отображает переданный HTML-элемент как ошибку */
    putNotification: function(not) {
        not.classList.add('popup-notification');
        not.classList.add('notice-hidden');
        not.addEventListener('click', function(e) {
            e.preventDefault();
            this.popNotification(not);
            return false;
        }.bind(this));
        setTimeout(function() {
            this.popNotification(not);
        }.bind(this), 10000);
        this.notifications.appendChild(not);
        not.offsetWidth;  // force reflow
        not.classList.remove('notice-hidden');
    },

    /** Скрывает переданный HTML-элемент, который был ранее отображён как уведомление */
    popNotification: function(not) {
        if (not.parentNode !== this.notifications || not.classList.contains('notice-hidden')) {
            return false;
        }
        not.classList.add('notice-hidden');
        setTimeout(function() {
            this.notifications.removeChild(not);
        }.bind(this), 300);
        return true;
    },

    /*
     * Просто addEventListener для нескольких объектов сразу
     */
    bind: function(selector, type, listener, useCapture) {
        var elements = Array.prototype.slice.apply(document.querySelectorAll(selector));
        for (var i = 0; i < elements.length; i++) {
            elements[i].addEventListener(type, listener, useCapture);
        }
        return elements.length;
    },

    /*
     * Отображение модального окна.
     * При force отображает, даже если какое-то модальное окно уже есть: заменяет его содержимое.
     * При norewrite не перезаписывает содержимое html-кодом из первого параметра; это позволяет
     * отобразить предусатнволенную в HTML-коде всплывашку.
     * На location, ajax, history и прочее никак не влияет.
     */
    modal: function(html, force, norewrite) {
        if (this.modalShow && !force) {
            return false;
        }

        if (!norewrite) {
            this.modalElement.innerHTML = html;
        }
        this.modalBackgr.classList.remove('hide');
        this.modalElement.classList.remove('hide');
        this.modalBackgr.offsetWidth; // force reflow
        this.modalBackgr.classList.add('in');
        this.modalElement.classList.add('in');

        this.bind('#modal [data-dismiss="modal"]', 'click', this._modalHideEvent.bind(this));
        this.modalShow = true;
        this.modalClosing = false;
        return true;
    },

    /*
     * Прячет модальное окно, открытое методом modal.
     * На location, ajax, history и прочее никак не влияет.
     */
    modalHide: function() {
        if (!this.modalShow || this.modalClosing) {
            return false;
        }
        this.modalClosing = true;
        this.modalElement.classList.remove('in');
        this.modalBackgr.classList.remove('in');
        setTimeout(function() {
            if (!this.modalClosing) {
                // Кто-то открыл модальное окно с force
                return;
            }
            this.modalBackgr.classList.add('hide');
            this.modalElement.classList.add('hide');
            this.modalElement.innerHTML = '';
            this.modalShow = false;
        }.bind(this), 300);
        return true;
    },

    /*
     * Обработка клика на фон модального окна или его кнопок закрытия.
     * Если оно было открыто через amajaxify при клике по ссылке,
     * то выполняет history.back() и модальное окно закрывается уже событием popstate.
     * Иначе просто вызывает modalHide и на location, ajax, history и прочее никак не влияет.
     */
    _modalHideEvent: function(event) {
        event.stopImmediatePropagation();
        event.preventDefault();
        if (window.amajaxify && window.amajaxify.isModalNow()) {
            window.history.back();
            return false;
        }
        this.modalHide();
        return false;
    },

    ajaxify: function() {
        var amajaxify = window.amajaxify;
        if (!amajaxify) {
            console.warn('amajaxify library is not found; AJAX is disabled');
            return;
        }

        if (document.cookie.indexOf('noajax=1') >= 0) {
            console.log('amajaxify disabled by cookie');
            return;
        }

        var initOk = amajaxify.init({
            customFetch: core.ajax.fetch.bind(core.ajax),
            withoutClickHandler: true,
            allowScriptTags: true,
            bindWithjQuery: true,
            updateModalFunc: function(html) {
                if (html !== null) {
                    this.modal(html, true);
                } else if (this.modalShow && !this.modalClosing) {
                    this.modalHide();
                }
            }.bind(this),
        });
        if (!initOk) {
            // maybe Wayback Machine
            return;
        }

        core.utils.setLiveClickListenerFallback(amajaxify.linkClickHandler.bind(amajaxify));

        document.addEventListener('amajaxify:load', this._ajaxLoadEvent.bind(this));
        document.addEventListener('amajaxify:unload', this._ajaxUnloadEvent.bind(this));

        document.addEventListener('amajaxify:error', this._ajaxErrorEvent.bind(this));

        document.addEventListener('amajaxify:beginrequest', this._ajaxBeginEvent.bind(this));
        document.addEventListener('amajaxify:endrequest', this._ajaxEndEvent.bind(this));
    },


    /*
     * Общие для большинства запросов обработчики ответа
     */
    handleResponse: function(data, url) {
        if (data.page_content) {
            window.amajaxify.handlePageData(url, data.page_content);
            return true;
        }
        if (!data.success) {
            this.notifyError(data.error || 'Ошибка');
            return true;
        }
        return false;
    },

    handleError: null, // см. init

    __handleError: function(exc) {
        console.error('Fetch error');
        console.error(exc);
        this.notifyError(exc.toString());
    },

    // amajaxify utils
    setLoading: function(isLoading) {
        if (isLoading) {
            this.loadingIcon.classList.remove('loader-hidden');
        } else {
            this.loadingIcon.classList.add('loader-hidden');
        }
    },

    _ajaxLoadEvent: function(event) {
        var i;

        if (event.detail.content.csrftoken) {
            core.ajax.setCsrfToken(event.detail.content.csrftoken);
        }

        if (event.detail.toModal) {
            if (event.detail.content.modal_content) {
                console.warn('modal_content is not available on modal page; looks like backend bug');
            }
            for (i = 0; i < this.loadModalCallbacks.length; i++) {
                this.loadModalCallbacks[i](this.modalElement);
            }

        } else {
            if (event.detail.content.modal_content) {
                this.modal(event.detail.content.modal_content);
            }

            for (i = 0; i < this.loadCallbacks.length; i++) {
                this.loadCallbacks[i](this.content);
            }
        }
    },

    _ajaxUnloadEvent: function(event) {
        var i;
        // Если текущая страница — модальное окно, выгружаем его
        if (window.amajaxify.isModalNow()) {
            for (i = 0; i < this.unloadModalCallbacks.length; i++) {
                this.unloadCallbacks[i](this.modalElement);
            }
        }

        // Если следующая страница не будет всплывающим окном, то выгружаем текущую
        if (!event.detail.toModal) {
            for (i = 0; i < this.unloadCallbacks.length; i++) {
                this.unloadCallbacks[i](this.content);
            }
        }
    },

    _ajaxBeginEvent: function() {
        this.setLoading(true);
    },

    _ajaxEndEvent: function() {
        this.setLoading(false);
    },

    _ajaxErrorEvent: function(event) {
        event.preventDefault();
        if (event.detail.response && event.detail.response.status >= 400) {
            this.notifyError('Ошибка ' + event.detail.response.status);
        } else {
            this.handleError(event.detail.exc);
        }
        return false;
    },
};


core.ajax = {
    csrfToken: null,

    getCsrfToken: function() {
        if (this.csrfToken === null) {
            this.csrfToken = document.querySelector('meta[name=csrf-token]').content;
        }
        return this.csrfToken;
    },

    setCsrfToken: function(token) {
        this.csrfToken = token;
        document.querySelector('meta[name=csrf-token]').content = token;
    },

    fetch: function(input, init) {
        var request;
        if (Request.prototype.isPrototypeOf(input) && !init) {
            request = input;
        } else {
            request = new Request(input, init);
        }
        request = new Request(request, {credentials: 'include'});
        request.headers.set('Accept', 'application/json,*/*');
        request.headers.set('X-AJAX', '1');
        if (request.method != 'GET') {
            request.headers.set('X-CSRFToken', this.getCsrfToken());
        }

        return fetch(request);
    },

    post: function(input, body, init) {
        init = init || {};
        init.method = 'POST';
        init.body = body;
        var request = new Request(input, init);
        return this.fetch(request);
    },

    postJSON: function(input, body, init) {
        init = init || {};
        init.method = 'POST';
        init.body = JSON.stringify(body);
        init.headers = init.headers || {};
        if (!init.headers['Content-Type']) {
            init.headers['Content-Type'] = 'application/json';
        }
        var request = new Request(input, init);
        return this.fetch(request);
    }
};


core.utils = {
    liveListeners: {},
    liveListenerFallback: null,

    init: function() {
        document.body.addEventListener('click', this._liveClick.bind(this));
    },

    addThisEventListener: function(obj, type, listener, useCapture) {
        var thisListener = function(event) {
            return listener(obj, event);
        };
        obj.addEventListener(type, thisListener, useCapture);
        return thisListener;  // for removeEventListener if needed
    },

    /**
     * Навешивание обработчика на элементы с определённым классом.
     * Отличие от простого addEventListener в том, что это не слетает при изменении DOM
     * (то есть отлично дружит с amajaxify); аналог jQuery live events
     */
    addLiveClickListener: function(className, listener) {
        if (!this.liveListeners.hasOwnProperty(className)) {
            this.liveListeners[className] = [];
        }
        this.liveListeners[className].push(listener);
    },

    /**
     * Обработчик клика по умолчанию, если на классы элемента, на который кликнули,
     * не прикреплено ни одного обработчика через addLiveClickListener или если
     * они не запретили действие по умолчанию
     */
    setLiveClickListenerFallback: function(func) {
        this.liveListenerFallback = func;
    },

    _liveClick: function(event) {
        var target = event.target || event.srcElement;

        // Перебираем элементы, пока не найдём тот, для класса которого есть обработчик
        while (!event.cancelBubble && target && target !== document.body) {
            // Перебираем классы, для которых есть обработчики
            for (var className in this.liveListeners) {
                if (!this.liveListeners.hasOwnProperty(className)) {
                    continue;
                }

                // Если у текущего элемента есть нужный класс
                if (target.classList.contains(className)) {
                    // Вызываем обработчики
                    for (var i = 0; i < this.liveListeners[className].length; i++) {
                        this.liveListeners[className][i](event, target);
                    }
                }
            }

            // Берём родителя и продолжаем дальше (если предыдущие обработчики не запретили всплытие)
            target = target.parentNode || target.parentElement;
        }

        // Если никто ничего не запретил, вызываем обработчик по умолчанию
        if (!event.cancelBubble && !event.defaultPrevented && this.liveListenerFallback) {
            this.liveListenerFallback(event);
        }
    }
};

document.addEventListener('DOMContentLoaded', core.init.bind(core)); // new browsers
document.addEventListener('load', core.init.bind(core)); // old browsers
