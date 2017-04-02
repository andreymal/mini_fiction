/*!
 * amajaxify.js (2017-04)
 * License: MIT
 * Библиотека для загрузки загрузки страниц и отправки форм с помощью
 * ES6 fetch и HTML5 History API для разных ништяков.
 * В отличие от аналогов вроде PJAX требует изменений на сервере, но зато
 * немного экономит трафик, гибче и поддерживает модальные окна.
 *
 * Генерирует следующие события на объекте document:
 *
 * - amajaxify:beginrequest(detail={method, url})
 *   Непосредственно перед отправкой запроса на сервер
 *
 * - amajaxify:unload(detail={url, content, toModal})
 *   Перед удалением старого содержимого страницы и загрузкой нового.
 *   В объекте event.detail передаётся инфfормация о будущем контенте
 *
 * - amajaxify:prepare(detail={url, content, toModal, preparedContent})
 *   Вызывается после amajaxify:unload и перед amajaxify:load; позволяет
 *   пропатчить ответ сервера по необходимости. Обработчики должны записать
 *   новые значения page_content в объект preparedContent, а в объекте content
 *   хранится оригинальный ответ сервера, и его никто трогать не должен.
 *
 * - amajaxify:load(detail={url, content, toModal})
 *   После загрузки всего нового содержимого страницы
 *
 * - amajaxify:error(detail={url, response, exc})
 *   Вызывается при ошибке получения ответа от сервера (unload/prepare/load
 *   при этом не вызываются). Объект response является тем, что вернул fetch()
 *   и может отсутствовать.
 *
 * - amajaxify:endrequest(detail={method, url})
 *   После полного завершения обработки запроса, после всех остальных событий
 *   независимо от того, ошибка или нет
 *
 * События beginrequest и endrequest появляются только в случае отправки
 * запроса самим amajaxify; если был вызван handlePageData напрямую, то
 * остаются только события unload/prepare/load.
 */


'use strict';


var amajaxify = {
    state: {
        v: null,
        enabled: false,
        initAt: null,
        current: null,
        isModalNow: false,
        loadedScripts: [],
        lastId: 0
    },
    modalSupport: false,
    allowScriptTags: false,

    customFetch: null,
    updateModalFunc: null,


    init: function(options) {
        options = options || {};

        if (!window.history || !window.history.pushState || !window.history.replaceState) {
            console.log('amajaxify: window.history is not supported, AJAX disabled');
            return false;
        }

        if (!options.force) {
            var archiveHosts = ['web.archive.org', 'archive.is', 'archive.today', 'archive.li', 'archive.fo', 'peeep.us'];
            if (archiveHosts.indexOf(location.hostname.toLowerCase()) >= 0) {
                console.log('amajaxify: Wayback Machine detected, AJAX disabled');
                return false;
            }
        }

        this.state.initAt = new Date().getTime();

        // Иногда бывает надобно присылать в HTML-коде скрипты (какие-нибудь яндекс-карты, например)
        this.allowScriptTags = options.allowScriptTags ? true : false;

        this.customFetch = options.customFetch;

        if (options.updateModalFunc) {
            this.updateModalFunc = options.updateModalFunc;
            this.modalSupport = true;
        }

        window.addEventListener('popstate', this._popstateEvent.bind(this));
        if (window.FormData) {
            window.addEventListener('submit', this._submitEvent.bind(this));
        }

        // Нужно сохранить изначальный state в истории
        this.updatePageState(null, null, true);

        // И ещё нужно сохранить уже выполненные скрипты, чтобы потом
        // при загрузке следующей страницы они не выполнялись повторно
        // и не вызывали глюков
        var scripts = document.getElementsByTagName('script');
        for (var i = 0; i < scripts.length; i++) {
            if (scripts[i].src) {
                this.state.loadedScripts.push(scripts[i].src);
            }
        }

        if (options.bindWithjQuery) {
            // Костыль для bootstrap и прочих вещей с jQuery:
            // Нативный listener выполняется раньше, чем jQuery live event в bootstrap,
            // отчего ломаются переключалки вкладок и спойлеры.
            // Поэтому если он здесь присутствует, то приходится тоже делать live event
            (window.$ || window.jQuery)(document).on('click', 'a', this.linkClickHandler.bind(this));
        } else if (!options.withoutClickHandler) {
            document.body.addEventListener('click', this.linkClickHandler.bind(this));
        } // else - кто-то должен повесить обработчик самостоятельно

        this.state.enabled = true;
        return true;
    },


    isEnabled: function() {
        return this.state.enabled;
    },


    isModalNow: function() {
        return this.state.isModalNow;
    },


    /**
     * Подгружает контент страницы по ajax со всеми необходимыми действиями:
     * history.pushState, unload/load, вот это вот всё.
     */
    goto: function(method, link, body, options) {
        if (!this.state.enabled) {
            console.warn('amajaxify: disabled, but goto was called');
            return false;
        }
        if (this.state.current !== null) {
            return false;
            // TODO: сделать наоборот отмену предыдущего запроса
        }

        method = method.toUpperCase();

        // Сохраняем информацию о запросе
        var current = {
            options: options || {},
            id: null, // установим позже
            response: null,
            next: null,
            request: [method, link]
        };

        // Якорь отправлять бессмысленно, но до него нужно будет прокрутить
        // после загрузки
        var hash = null;
        var f = link.indexOf('#');
        if (f > 0) {
            hash = link.substring(f + 1);
            link = link.substring(0, f);
        }
        current.options.hash = hash;

        // Кастомная функция fetch может добавлять CSRF-токен, куки и прочее
        var fetchFunc = this.customFetch || window.fetch;

        // Сохраняем инфу о запросе
        current.id = ++this.state.lastId;
        this.state.current = current;
        if (this.state.lastId === 32767) {
            this.state.lastId = -32769;
        }

        // Собственно отправляем запрос
        this._dispatchEvent('amajaxify:beginrequest', {method: method, url: link});
        fetchFunc(link, {method: method, body: body, redirect: 'error'})
            .then(function(response) {
                this.state.current.response = response;
                return response.json();
            }.bind(this))
            .then(this._linkAjaxResponse.bind(this))  // onload
            .then(null, this._linkAjaxFailed.bind(this))  // onerror (.catch not working with IE8)
            .then(this._linkAjaxFinished.bind(this));  // onend

        return true;
    },

    /**
     * Перехват кликов по любым ссылкам на странице
     */
    linkClickHandler: function(event) {
        if (event.isDefaultPrevented !== undefined && event.isDefaultPrevented()) {
            // костыль для bootstrap/jQuery (см. init)
            return false;
        }
        if (!this.state.enabled || event.defaultPrevented) {
            return;
        }

        if ((event.which || event.button) !== 1) {
            // Если кликнули не левую кнопку мыши
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
        if (target.getAttribute('data-noajax') == '1') {
            return;
        }

        var href = target.href;
        var host = (location.origin || (location.protocol + '//' + location.host));

        // Если ссылка различается только якорем, то просто меняем его (браузер прокрутит всё сам)
        var h = href.indexOf('#');
        if (h > 0) {
            var currentPage = location.toString();
            if (currentPage.indexOf('#') > 0) {
                currentPage = currentPage.substring(0, currentPage.indexOf('#'));
            }
            var hrefPage = href.substring(0, h);
            if (currentPage == hrefPage) {
                history.pushState(history.state, '', href.substring(h));
                return;
            }
        }

        // Проверяем, что она в пределах хоста
        if (target.target || (href.indexOf(host + '/') !== 0 && href != host)) {
            // Если другой хост или target="_blank", то браузер сделает всё сам
            return;
        }

        // Всё норм, переходим
        this.goto('GET', href);

        event.stopImmediatePropagation();
        event.preventDefault();
        return false;
    },

    _linkAjaxResponse: function(data) {
        // Обработчик ответа сервера, который должен прислать
        // pageContent или page_content
        var content = data.pageContent || data.page_content;

        if (!content || data.pageContent && data.page_content) {
            throw new Error('amajaxify: incorrect server response');
        }

        this.handlePageData(this.state.current.response.url, content, this.state.current.options);
    },

    handlePageData: function(url, content, options) {
        /* Обрабатывает указанные данные, обновляя страницу и вызывая события
        unload/prepare/load.

        Формат объекта content:
        {
            // при изменении этого значения в одном из запросов будет
            // принудительно обновлена страница при следующем клике
            "v": any,

            // при наличии будет произведён переход на указанную страницу
            // средствами браузера без всяких ajax (текущая страница
            // выгрузится)
            "replace": "ссылка",

            // при наличии будет немедленно отправлен ajax-запрос на указанный
            // адрес, а data, modal и title будут проигнорированы
            "redirect": "ссылка",

            // при наличии будет отображено модальное окно, считающееся
            // полноценной страницей, а data проигнорирован; при его закрытии
            // будет изменена адресная строка
            "modal": "html-код",

            // что на что заменить на странице
            "data": {"id элемента": "html-код", ...},

            // элементы, которые добавить в head; будут удалены при выгрузке
            "head": "html-код",

            // заголовок страницы (да, именно html-код ради &mdash; и прочего)
            "title": "html-код",

            // список ссылок к скриптам, которые надобно выполнить строго один раз
            // (для скриптов, запускаемых при каждой перезагрузке страницы,
            // используйте обычный тег <script> в "data")
            "scripts": ["/path/to/script.js", ...],

            // плюс что угодно ещё для обработки сторонними обработчиками
        }

        options может содержать:
        - replaceState (true/false) — если нужно заменить текущую сслыку
          в истории, а не добавлять новую
        - noScroll (true/false) — не прокручивать страницу вверх после
          обновления страницы

        */

        if (content.replace) {
            // Сервер нас просит открыть страницу без ajax
            window.location = content.replace;
            return;
        }
        if (content.redirect) {
            // Сервер просит нас провести редирект
            // (костыль в связи с трудностями с выяснением настоящей ссылки
            // после нормального редиректа; если в будущем это не проблема,
            // данную штуку можно убрать)
            if (this.state.current) {
                this.state.current.next = content.redirect;
            } else {
                setTimeout(function() {
                    this.goto('GET', content.redirect);
                }.bind(this), 0);
            }
            return;
        }

        var toModal = content.modal && this.modalSupport;

        // TODO: здесь не забыть:
        // - csrftoken
        // - popup (как modal, но не полноценная страница)

        this._linkAjaxDisableIfNeeded(content);

        if (toModal) {
            // Установка модального окна
            this._dispatchEvent('amajaxify:unload', {url: url, content: content, toModal: toModal});

            this.updateModalFunc(content.modal);
            this.state.isModalNow = true;
            if (content.title) {
                document.head.getElementsByTagName('title')[0].innerHTML = content.title;
            }
            this.updatePageState(url, content.title, options);

            this._dispatchEvent('amajaxify:load', {url: url, content: content, toModal: toModal});

        } else if (content.modal) {
            // Установка модального окна обломилась
            console.warn('amajaxify: server returned content for modal window, but this is not configured; ignored');

        } else {
            // Установка обычного контента страницы
            this._dispatchEvent('amajaxify:unload', {url: url, content: content, toModal: toModal});

            if (this.modalSupport) {
                this.updateModalFunc(null);
            }
            this.state.isModalNow = false;

            // Позволяем обработчикам пошаманить по необходимости
            var readyContent = this._prepareContent(url, content, toModal);

            this.setHead(readyContent.head);
            if (readyContent.title) {
                document.head.getElementsByTagName('title')[0].innerHTML = readyContent.title;
            }
            this.setPageData(readyContent.data);
            this.updatePageState(url, readyContent.title, options);

            // Запускаем скрипты (только те, которые ещё не запускались когда-то раньше)
            if (readyContent.scripts) {
                for (var i = 0; i < readyContent.scripts.length; i++) {
                    var spath = readyContent.scripts[i];
                    var s = document.createElement('script');
                    s.src = spath; // Используем потом s.src вместо spath, ибо нормализованная ссылка
                    if (this.state.loadedScripts.indexOf(s.src) >= 0) {
                        continue;
                    }
                    document.body.appendChild(s);
                    this.state.loadedScripts.push(s.src);
                }
            }

            this._dispatchEvent('amajaxify:load', {url: url, content: readyContent, toModal: toModal});
        }
    },

    _prepareContent: function(url, content, toModal) {
        var k;
        var preparedContent = {
            data: {},
        };
        for (k in content.data) {
            if (content.data.hasOwnProperty(k)) {
                preparedContent.data[k] = content.data[k];
            }
        }
        this._dispatchEvent('amajaxify:prepare', {url: url, content: content, toModal: toModal, preparedContent: preparedContent});

        // Собираем необработанное и обработанное в кучу
        var readyContent = {};
        for (k in content) {
            if (content.hasOwnProperty(k)) {
                readyContent[k] = content[k];
            }
        }
        for (k in preparedContent) {
            if (preparedContent.hasOwnProperty(k)) {
                readyContent[k] = preparedContent[k];
            }
        }

        return readyContent;
    },

    updatePageState: function(url, title, options) {
        options = options || {};

        var titleElem = document.head.getElementsByTagName('title')[0];
        if (title === undefined || title === null) {
            title = titleElem.innerHTML;
        }
        if (url === undefined || url === null) {
            url = location.toString();
        }

        var state = {
            amajaxify: true,
            isModalNow: this.state.isModalNow,
            title: title
        };

        // Тут такое дело: бэкенд через проксю не всегда не может опеределить, что
        // идёт https-запрос, и в X-Request-URL пихает http-ссылку. А параноик
        // старый Safari (в котором используется полифилл к fetch) ругается на
        // несоответствие протоколов, так что для него мы его обрежем
        if (fetch.polyfill && url.indexOf('://') > 0) {
            url = url.substring(url.indexOf('://') + 1);
        }

        if (!options.replaceState) {
            history.pushState(state, '', url);
        } else {
            history.replaceState(state, '', url);
        }

        if (!options.noScroll && !this.state.isModalNow && window.scrollY > 400) {
            window.scrollTo(0, 0);
        }
    },

    _linkAjaxDisableIfNeeded: function(content) {
        // Если версия статики не совпадает с нашей, то пришло время обновлять страницу полностью
        if (content.v) {
            if (this.state.v !== null && this.state.v !== content.v) {
                this.state.enabled = false;
            } else if (this.state.v === null) {
                this.state.v = content.v;
            }
        }

        // Да и через часик обновить тоже не будет лишним
        if (new Date().getTime() - this.state.initAt > 3600000) {
            this.state.enabled = false;
        }
    },

    _linkAjaxFailed: function(exc) {
        var url = null;
        var response = this.state.current ? this.state.current.response : null;
        if (response) {
            url = this.state.current.response.url;
        }
        if (this._dispatchEvent('amajaxify:error', {url: url, response: response, exc: exc})) {
            console.error(exc);
        }
    },

    _linkAjaxFinished: function() {
        this._dispatchEvent('amajaxify:endrequest', {
            method: this.state.current.request[0],
            url: this.state.current.request[1]
        });
        var next = this.state.current.next;
        this.state.current = null;
        if (next) {
            this.goto('GET', next);
        }
    },

    /**
     * Обработка нажатия кнопок Назад/Вперёд браузера
     */
    _popstateEvent: function(event) {
        if (!event.state || !event.state.amajaxify) {
            // Это какой-то не наш state (например, баганутый Safari всегда вызывает popstate после onload)
            // FIXME: Иногда это бывает нажатие «Назад» после обновления страницы, и это надо обработать,
            // но хз как чтоб с Safari не накосячить
            return;
        }
        if (!this.state.enabled) {
            window.location.reload();
            return;
        }
        if (this.state.isModalNow && (!event.state || !event.state.isModalNow)) {
            // Если контент текущей страницы в модальном окне, а предыдущей/следующей
            // не в модальном, то просто прячем окно и больше ничего не делаем
            this.updateModalFunc(null);
            this.state.isModalNow = false;
            if (event.state && event.state.title) {
                document.head.getElementsByTagName('title')[0].innerHTML = event.state.title;
            }
            // FIXME: при нажатии «Вперёд» при модальном окне контент не совпадает с ссылкой,
            // но без сохранения старого location не починить
            return;
        } else if (!this.state.isModalNow && this.modalSupport) {
            // Но прятать окна, не являющиеся страницами, в любом случае надо (NSFW-предупреждение, например)
            this.updateModalFunc(null);
        }
        // Здесь в принципе можно организовать кэширование, но нужно ли?
        if (!this.goto('GET', location.toString(), undefined, {replaceState: true, noScroll: true})) {
            console.warn('amajaxify: failed to popstate');
        }
    },

    /*
     * Перехват отправки любой формы
     */
    _submitEvent: function(event) {
        var form = event.target || event.srcElement;
        if (form.getAttribute('data-noajax') == '1' || !this.state.enabled || event.defaultPrevented) {
            return;
        }

        var href = form.action || location.toString();
        var host = (location.origin || (location.protocol + '//' + location.host)) + '/';
        if (href.indexOf(host) !== 0) {
            return;
        }

        var formData = new FormData(form);
        // Нам не предоставили способа получить нажатую кнопочку отправки, костыляем
        // FIXME: для <input form="formid" /> за пределами формы не работает, разумеется
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
    },

    setHead: function(head, onload) {
        if (!head) {
            if (onload) {
                onload();
            }
            return;
        }
        var i, e;

        // TODO: css preloading?
        // FIXME: it requires refactoring of _linkAjaxFinished

        var headDOM = document.createElement('head');
        headDOM.innerHTML = head;
        var newHeadElements = Array.prototype.slice.call(headDOM.children);
        headDOM = null;

        // Удаляем старые элементы
        var oldHeadElements = Array.prototype.slice.call(document.getElementsByClassName('amajaxify-head'));
        for (i = 0; i < oldHeadElements.length; i++) {
            e = oldHeadElements[i];
            e.parentNode.removeChild(e);
        }
        oldHeadElements = null;

        // Добавляем новые элементы
        for (i = 0; i < newHeadElements.length; i++) {
            e = newHeadElements[i];
            e.classList.add('amajaxify-head');
            document.head.appendChild(e);
        }

        if (onload) {
            setTimeout(onload, 1000);
        }
    },

    setPageData: function(data) {
        for (var key in data) {
            if (!data.hasOwnProperty(key)) {
                continue;
            }
            var elem = document.getElementById(key);
            if (elem) {
                elem.innerHTML = data[key];
                if (this.allowScriptTags) {
                    this._startElemScripts(elem);
                }
            } else {
                console.warn('amajaxify: received content for #' + key + ', but element not found');
            }
        }
    },

    _startElemScripts: function(elem) {
        var scripts = Array.prototype.slice.call(elem.getElementsByTagName('script'));
        for (var i = 0; i < scripts.length; i++) {
            var s = scripts[i];
            var s2 = document.createElement('script');
            if (s.src) {
                s2.src = s.src;
            }
            if (s.type) {
                s2.type = s.type;
            }
            if (s.language) {
                s2.language = s.language;
            }
            if (s.innerHTML) {
                s2.innerHTML = s.innerHTML;
            }
            // Проверка на наличие скрипта в this.state.loadedScripts здесь не нужна,
            // так как оно только для поля "scripts" в json-ответе сервера
            s.parentNode.insertBefore(s2, s);
            s.parentNode.removeChild(s);
        }
    },

    _createEvent: function(name, detail) {
        try {
            // DOM L4
            return new CustomEvent(name, {cancelable: true, detail: detail || {}});
        } catch (e) {
            // DOM L3
            var event = document.createEvent('CustomEvent');
            event.initCustomEvent(name, true, true, detail || {});
            return event;
        }
    },

    _dispatchEvent: function(name, params) {
        return document.dispatchEvent(this._createEvent(name, params));
    }
};
