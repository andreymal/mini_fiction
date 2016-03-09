'use strict';


var core = {
    modulesList: [],
    unloadQueue: [],
    unloadModalQueue: [],
    csrftoken: null,
    nav: null,
    content: null,

    modalShow: false,
    modalElement: null,
    modalBackgr: null,
    loadingIcon: null,
    notifications: null,

    loaded: false,
    loadedModal: false,

    state: {
        enabled: window.history !== undefined && window.history.pushState !== undefined,
        current: null, // информация о текущем ajax-запросе
        lastId: 0, // id последнего ajax-запроса
        modal: false, // является ли текущая «страница» модальным окном
        v: null,
        initAt: null,
    },

    /*
     * Подключение модуля
     * (нужно в первую очередь для вызова у него unload/load при кликах по ссылкам)
     */
    define: function(name, module) {
        if (this[name] !== undefined) {
            throw new Error('Conflict');
        }
        this[name] = module;
        this.modulesList.push(name);
    },

    /*
     * Инициализация всего этого дела
     */
    init: function() {
        this.handleError = this.__handleError.bind(this);

        this.nav = document.getElementById('nav-main');
        this.content = document.getElementById('content');
        this.modalElement = document.getElementById('modal');
        this.modalBackgr = document.getElementById('modal-bg');
        this.modalBackgr.addEventListener('click', this._modalHideEvent.bind(this));
        this.loadingIcon = document.getElementById('loading-icon');
        this.notifications = document.getElementById('notifications');

        // прикручивание ajax всем ссылкам и формам; если не нравится, можно убрать
        if (this.state.enabled) {
            // document.body.addEventListener('click', this._linkClickEvent);
            // Нативный listener выполняется раньше, чем jQuery live event в bootstrap,
            // отчего ломаются переключалка вкладок в справке и спойлеры.
            // Поэтому, пока он здесь присутствует, приходится тоже делать live event
            $(document).on('click', 'a', this._linkClickEvent);

            window.addEventListener('popstate', this._popstateEvent.bind(this));
            if (window.FormData) {
                window.addEventListener('submit', this._submitEvent.bind(this));
            }

            // Сохраняем заголовок в стеке истории
            history.replaceState({
                modal: false,
                title: document.head.getElementsByTagName('title')[0].innerHTML,
            }, '', location.toString());
        }

        for (var i = 0; i < this.modulesList.length; i++) {
            var module = this[this.modulesList[i]];
            if (module.hasOwnProperty('init')) {
                try {
                    module.init();
                } catch (e) {
                    console.error(e);
                }
            }
        }

        this.state.initAt = new Date().getTime();

        this.load();

        // Показываем предустановленное модальное окно
        if (this.modalElement.childNodes.length > 0) {
            this.modal(null, true, true);
        }
    },

    /*
     * Загрузка подключенных модулей после завершения загрузки DOM (в т.ч. через ajax)
     */
    load: function() {
        if (this.loaded) {
            return false;
        }
        for (var i = 0; i < this.modulesList.length; i++) {
            var module = this[this.modulesList[i]];
            if (module.hasOwnProperty('unload')) {
                this.unloadQueue.push(module);
            }
            if (module.hasOwnProperty('load')) {
                try {
                    module.load(this.content);
                } catch (e) {
                    console.error(e);
                }
            }
        }
        // $('#content .bootstrap').each(stuff.bootstrap); // TODO: в модуль
        this.loaded = true;
        return true;
    },

    /*
     * Выгрузка подключенных модулей перед заменой содержимого страницы на полученное через ajax
     */
    unload: function() {
        if (!this.loaded) {
            return false;
        }
        for (var i = this.unloadQueue.length - 1; i >= 0; i--) {
            try {
                this.unloadQueue[i].unload(this.content);
            } catch (e) {
                console.error(e);
            }
        }
        this.unloadQueue = [];
        this.loaded = false;
        return true;
    },

    /*
     * Загрузка подключенных модулей после завершения загрузки DOM модального окна
     */
    loadModal: function() {
        if (this.loadedModal) {
            return false;
        }
        for (var i = 0; i < this.modulesList.length; i++) {
            var module = this[this.modulesList[i]];
            if (module.hasOwnProperty('unloadModal')) {
                this.unloadModalQueue.push(module);
            }
            if (module.hasOwnProperty('loadModal')) {
                try {
                    module.loadModal(this.modalElement);
                } catch (e) {
                    console.error(e);
                }
            }
        }
        this.loadedModal = true;
        return true;
    },

    /*
     * Выгрузка подключенных модулей перед заменой содержимого или скрытия модального окна
     */
    unloadModal: function() {
        if (!this.loadedModal) {
            return false;
        }
        for (var i = this.unloadModalQueue.length - 1; i >= 0; i--) {
            try {
                this.unloadModalQueue[i].unloadModal(this.modalElement);
            } catch (e) {
                console.error(e);
            }
        }
        this.unloadModalQueue = [];
        this.loadedModal = false;
        return true;
    },

    notify: function(text) {
        var not = document.createElement('div');
        not.textContent = text;
        this.putNotification(not);
    },

    notifyError: function(text) {
        var not = document.createElement('div');
        not.classList.add('notice-error');
        not.textContent = text;
        this.putNotification(not);
    },

    putNotification: function(not) {
        not.classList.add('notification');
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

    popNotification: function(not) {
        if (not.parentNode !== this.notifications || not.classList.contains('notice-hidden')) {
            return false;
        }
        not.classList.add('notice-hidden');
        setTimeout(function() {
            this.notifications.removeChild(not);
        }, 300);
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
        return true;
    },

    /*
     * Прячет модальное окно, открытое методом modal.
     * На location, ajax, history и прочее никак не влияет.
     */
    modalHide: function() {
        if (!this.modalShow) {
            return false;
        }
        this.modalElement.classList.remove('in');
        this.modalBackgr.classList.remove('in');
        setTimeout(function() {
            this.modalBackgr.classList.add('hide');
            this.modalElement.classList.add('hide');
            this.modalElement.innerHTML = '';
            this.modalShow = false;
        }.bind(this), 300);
        return true;
    },

    /*
     * Обработка клика на фон модального окна или его кнопок закрытия.
     * Если оно было открыто через ajax при клике по ссылке (точнее, при вызове setContent),
     * то выполняет history.back() и модальное окно закрывается уже событием popstate.
     * Иначе просто вызывает modalHide и на location, ajax, history и прочее никак не влияет.
     */
    _modalHideEvent: function(event) {
        event.stopImmediatePropagation();
        event.preventDefault();
        if (this.state.modal) {
            window.history.back();
            return false;
        }
        this.modalHide();
        return false;
    },

    /*
     * Подгружает контент страницы по ajax со всеми необходимыми действиями:
     * history.pushState, unload/load, вот это вот всё.
     */
    goto: function(method, link, body, options) {
        if (this.state.current !== null) {
            return false;
            // TODO: сделать наоборот отмену предыдущего запроса
        }
        var current = {
            options: options || {},
            id: ++this.state.lastId,
            response: null,
            next: null,
            request: [method, link]
        };
        this.state.current = current;
        if (this.state.lastId === 32767) {
            this.state.lastId = -32769;
        }

        var hash = null;
        var f = link.indexOf('#');
        if (f > 0) {
            hash = link.substring(f + 1);
            link = link.substring(0, f);
        }
        current.options.hash = hash;

        this.loadingIcon.classList.remove('loader-hidden');
        this.ajax.fetch(link, {method: method, body: body, redirect: 'error'})
            .then(function(response) {
                this.state.current.response = response;
                return response.json();
            }.bind(this))
            .then(this._linkAjaxResponse.bind(this))
            .catch(this._linkAjaxFailed.bind(this))
            .then(this._linkAjaxFinished.bind(this));
    },

    /*
     * Устанавливает контент страницы (обычно полученный по ajax методом goto).
     * data является объектом с атрибутами modal (true/false), nav и content (код
     * соответствующих блоков). При указанном link делает history.pushState.
     */
    setContent: function(data, link, options) {
        options = options || {};

        if (data.modal && data.modal_content) {
            // modal_content для случая, когда надо загрузить окошко одновременно
            // с загруженной страницей (например, предупреждение NSFW).
            // А показывать два модальных окна одновременно нереально
            throw new Error('Arguments conflict');
        }

        // Выгрузка модулей

        // В любом случае нам выгружать модальное окно
        if (this.state.modal) {
            this.unloadModal();
        }

        // Если новый контент не для модального окна, то выгружаем модули, привязанные к контенту
        if (!data.modal) {
            this.unload();
        }

        if (!data.modal && this.state.modal) {
            this.modalHide();
        }

        // innerHTML для &mdash; -> — и подобного
        if (data.title) {
            document.head.getElementsByTagName('title')[0].innerHTML = data.title;
        }
        if (data.modal) {
            this.modal(data.content, true);
        } else {
            this.nav.innerHTML = data.nav;
            this.content.innerHTML = data.content;
        }
        if (link !== undefined && !options.nopushstate) {
            history.pushState({modal: data.modal, title: data.title}, '', link);
        }
        if (!options.noscroll && !data.modal && window.scrollY > 400) {
            window.scrollTo(0, 0);
        }
        if (options.hash) {
            // FIXME: это добавляет лишнюю запись в историю, переделать бы
            // (просто pushState нельзя, тогда прокрутка к элементу ломается)
            location.hash = options.hash;
        }
        this.state.modal = data.modal;

        if (data.modal_content) {
            // На момент написания loadModal и unloadModal решено здесь не вызывать
            // (если приспичит вызывать, то в init надо будет вызывать тоже)
            this.modal(data.modal_content);
        }

        if (!data.modal) {
            // Если новый контент не для модального окна, то загружаем модули, привязанные к контенту
            this.load();
        } else {
            // Иначе — к модальному окну
            this.loadModal();
        }

        // Костыль для того, что нам неподконтрольно (пока что)
        if (window.grecaptcha) {
            window.grecaptcha.reset();
        }

        // Не всё легко написать нормально — Flask-WTF RecaptchaField, например, вставляет <script>
        this.enableScriptTags(this.content);
    },

    enableScriptTags: function(elem) {
        var scripts = Array.prototype.slice.call(elem.getElementsByTagName('script'));
        for (var i = 0; i < scripts.length; i++) {
            var s = scripts[i];
            var parent = s.parentNode || s.parentElement;
            var next = s.nextElementSibling || null;
            parent.removeChild(s);

            var s2 = document.createElement('script');
            if (s.src) {
                s2.src = s.src;
            }
            if (s.type) {
                s2.type = s.type;
            }
            s2.innerHTML = s.innerHTML;
            if (next) {
                parent.insertBefore(s2, next);
            } else {
                parent.appendChild(s2);
            }
        }
    },

    /*
     * Общие для большинства запросов обработчики ответа
     */
    handleResponse: function(data, url) {
        if (this.handleResponsePage(data, url)) {
            return true;
        }
        if (!data.success) {
            this.notifyError(data.error || 'Ошибка');
            return true;
        }
        return false;
    },

    handleResponsePage: function(data, url) {
        if (!data.page_content) {
            return false;
        }
        if (data.page_content.redirect) {
            if (this.state.current) {
                this.state.current.next = data.page_content.redirect;
            } else {
                this.goto('GET', data.page_content.redirect);
            }
        } else {
            if (data.page_content.csrftoken) {
                this.ajax.setCsrfToken(data.page_content.csrftoken);
            }
            core.setContent(data.page_content, url);
        }
        return true;
    },

    handleError: null, // см. init

    __handleError: function(exc) {
        console.error('Fetch error with state', this.state.current);
        console.error(exc);
        this.notifyError(exc.toString());
    },

    /*
     * Перехват кликов по любым ссылкам на странице
     */
    _linkClickEvent: function(event) {
        if (event.isDefaultPrevented !== undefined && event.isDefaultPrevented()) {
            // костыль (см. init)
            return false;
        }
        if (!core.state.enabled || event.defaultPrevented) {
            return;
        }

        // Ищем ссылку, по которой кликнули
        var target = event.target || event.srcElement;
        while (target && target.tagName.toLowerCase() != 'a' && target !== document.body) {
            target = target.parentNode || parent.srcElement;
        }
        if (!target || target == document.body) {
            return;
        }

        // Проверяем, что её можно обрабатывать
        if (target.dataset.noajax == '1') {
            return;
        }

        var href = target.href;
        var host = (location.origin || (location.protocol + '//' + location.host));

        // Если ссылка различается только якорем, то просто меняем его
        var h = href.indexOf('#');
        if (h > 0) {
            var currentPage = location.toString();
            if (currentPage.indexOf('#') > 0) {
                currentPage = currentPage.substring(0, currentPage.indexOf('#'));
            }
            var hrefPage = href.substring(0, h);
            if (currentPage == hrefPage) {
                location.hash = href.substring(h + 1);
                return;
            }
        }

        // Проверяем, что она в пределах хоста
        if (target.target || (href.indexOf(host + '/') !== 0 && href != host)) {
            // Если другой хост или target="_blank", то браузер сделает всё сам
            return;
        }

        // Всё норм, переходим
        core.goto('GET', href);

        event.stopImmediatePropagation();
        event.preventDefault();
        return false;
    },

    _linkAjaxResponse: function(data) {
        if (!data.page_content) {
            throw new Error('Incorrect server response');
        }
        if (data.page_content.redirect) {
            this.state.current.next = data.page_content.redirect;
            return;
        }
        if (data.page_content.csrftoken) {
            this.ajax.setCsrfToken(data.page_content.csrftoken);
        }

        this._linkAjaxDisableIfNeeded(data);
        this.setContent(data.page_content, this.state.current.response.url, this.state.current.options);
    },

    _linkAjaxDisableIfNeeded: function(data) {
        // Если версия статики не совпадает с нашей, то пришло время обновлять страницу полностью
        if (data.page_content.v) {
            if (this.state.v !== null && this.state.v !== data.page_content.v) {
                this.state.enabled = false;
            } else if (this.state.v === null) {
                this.state.v = data.page_content.v;
            }
        }

        // Да и через часик обновить тоже не будет лишним
        if (new Date().getTime() - this.state.initAt > 3600000) {
            this.state.enabled = false;
        }
    },

    _linkAjaxFailed: function(exc) {
        this.handleError(exc);
    },

    _linkAjaxFinished: function() {
        // Так как даже ES6 fetch не даёт перехватывать редиректы,
        // бэкенд присылает нам редирект через json, и после завершения
        // обработки запроса мы здесь сами редиректимся
        var next = this.state.current.next;
        this.state.current = null;
        if (next) {
            this.goto('GET', next);
        } else {
            this.loadingIcon.classList.add('loader-hidden');
        }
    },

    /*
     * Обработка нажатия кнопок Назад/Вперёд браузера
     */
    _popstateEvent: function(event) {
        if (this.state.modal && (!event.state || !event.state.modal)) {
            // Если контент текущей страницы в модальном окне, а предыдущей/следующей
            // не в модальном, то просто прячем окно и больше ничего не делаем
            this.state.modal = false;
            this.unloadModal();
            this.modalHide();
            if (event.state && event.state.title) {
                document.head.getElementsByTagName('title')[0].innerHTML = event.state.title;
            }
            return;
        } else {
            // Но окошко прятать в любом случае надо (NSFW-предупреждение, например)
            this.modalHide();
        }
        // Здесь в принципе можно организовать кэширование, но нужно ли?
        this.goto('GET', location.toString(), undefined, {nopushstate: true, noscroll: true});
    },

    /*
     * Перехват отправки любой формы
     */
    _submitEvent: function(event) {
        var form = event.target || event.srcElement;
        if (form.dataset.noajax == '1' || !this.state.enabled || event.defaultPrevented) {
            return;
        }

        var href = form.action || location.toString();
        var host = (location.origin || (location.protocol + '//' + location.host)) + '/';
        if (href.indexOf(host) !== 0) {
            return;
        }

        var formData = new FormData(form);
        // Нам не предоставили способа получить нажатую кнопочку отправки, костыляем
        var submitButton = form.querySelector('input[type="submit"]:focus, button[type="submit"]:focus');
        // Если форму отправляют клавишей Enter, то нужно брать первую попавшуюся кнопку
        submitButton = submitButton || form.querySelector('input[type="submit"], button[type="submit"]');

        if (submitButton && submitButton.name) {
            formData.append(submitButton.name, submitButton.value || '');
        }

        var method = (form.method || 'GET').toUpperCase();
        if (method == 'GET') {
            if (formData.entries === undefined) {
                // Ждём реализации в других браузерах
                return;
            }
            var started = href.indexOf('?') > 0;
            var i, entry;
            for (i = formData.entries(); !(entry = i.next()).done;) {
                href += (started ? '&' : '?') + encodeURIComponent(entry.value[0]) + '=' + encodeURIComponent(entry.value[1]);
                started = true;
            }
        }
        this.goto(form.method, href, method != 'GET' ? formData : undefined);
        event.preventDefault();
        return false;
    }
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


document.addEventListener('DOMContentLoaded', core.init.bind(core));
