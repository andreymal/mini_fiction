/*!
 * amajaxify.js (2017-12)
 * License: MIT
 * Библиотека для загрузки загрузки страниц и отправки форм с помощью
 * ES6 fetch и HTML5 History API для разных ништяков.
 * В отличие от аналогов вроде PJAX требует изменений на сервере, но зато
 * немного экономит трафик, гибче и поддерживает модальные окна.
 */


'use strict';

/**
 * Собственно главный и единственный модуль.
 *
 * Когда инициализирован, генерирует следующие события на объекте document:
 *
 * - `amajaxify:beginrequest(detail={method, url})`
 *
 *   Непосредственно перед отправкой запроса на сервер
 *
 * - `amajaxify:unload(detail={url, content, toModal})`
 *
 *   Перед удалением старого содержимого страницы и загрузкой нового.
 *   В объекте event.detail передаётся инфfормация о будущем контенте.
 *   toModal содержит будущее состояние модального окна; чтобы узнать текущее
 *   состояние (отображается ли модальное окно прямо сейчас, ещё перед
 *   выгрузкой старого содержимого), можно использовать метод isModalNow.
 *
 * - `amajaxify:prepare(detail={url, content, toModal, preparedContent})`
 *
 *   Вызывается после `amajaxify:unload` и перед `amajaxify:load;` позволяет
 *   пропатчить ответ сервера по необходимости. Обработчики должны записать
 *   новые значения page_content в объект preparedContent, а в объекте content
 *   хранится оригинальный ответ сервера, и его никто трогать не должен.
 *   На данный момент toModal всегда false; перед запуском события содержимое
 *   страницы ещё не меняется (за исключением действий в обработчиках unload),
 *   так что метод isModalNow сообщает, является ли текущая страница, которая
 *   будет потом выгружена, модальным окном.
 *
 * - `amajaxify:load(detail={url, content, toModal})`
 *
 *   После загрузки всего нового содержимого страницы. toModal совпадает с
 *   isModalNow
 *
 * - `amajaxify:error(detail={url, response, exc})`
 *
 *   Вызывается при ошибке получения ответа от сервера (unload/prepare/load
 *   при этом не вызываются). Объект response является тем, что вернул fetch,
 *   и может отсутствовать.
 *
 * - `amajaxify:endrequest(detail={method, url})`
 *
 *   После полного завершения обработки запроса, после всех остальных событий
 *   независимо от того, ошибка или нет
 *
 * События `beginrequest` и `endrequest` появляются только в случае отправки
 * запроса самим amajaxify; если был вызван `handlePageData` напрямую, то
 * остаются только события unload/prepare/load.
 *
 * В случае закрытия модального окна без перезагрузки основного контента
 * страницы ничего кроме `updateModalFunc(null)` не вызывается.
 *
 * @module
 */
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
    allowScriptTags: false,
    scrollToTopFrom: 400,
    maxLifetime: 3600,

    customFetch: null,
    updateModalFunc: null,

    archiveHosts: [
        'web.archive.org', 'archive.is', 'archive.today', 'archive.li',
        'archive.fo', 'peeep.us', 'webcitation.org',
        'webcache.googleusercontent.com', 'hghltd.yandex.net',
        'cc.bingj.com', 'nova.rambler.ru'
    ],

    // костыль по вычислению активной кнопки формы
    _clickedBtn: null,
    _clickedBtnTimer: null,


    /**
     * Инициализирует amajaxify: вешает обработчики, вызывает replaceState,
     * всё такое. Возвращает true при успехе.
     *
     * @param {Object} [options] - дополнительные опции
     * @param {boolean} [options.force=false] - при true игнорирует некоторые
     *   ситуации, в которых лучше не запускаться, например, веб-архивы
     * @param {boolean} [options.allowScriptTags=false] - позволяет скриптам
     *   из HTML-кода, который прислал сервер, запускаться
     * @param {number} [options.scrollToTopFrom=400] - минимальная прокрутка
     *   по вертикали, при которой прокручивать обратно наверх после замены
     *   содержимого страницы
     * @param {Function} [options.updateModalFunc] - функция, которая будет
     *   вызываться для запихивания HTML-кода модального окна на страницу
     *   (после события unload и перед prepare и load), должна принимать один
     *   аргумент: HTML-код (null означает закрытие модального окна)
     * @param {Function} [options.customFetch] - своя функция fetch, которая
     *   будет использоваться вместо window.fetch (пригодится для добавления
     *   CSRF-токенов и подобного)
     * @param {boolean} [options.bindWithjQuery=false] - использовать jQuery
     *   для события onclick (решает некоторые проблемы с bootstrap)
     * @param {Function} [options.jQueryRef=undefined] - ссылка на jQuery
     * @param {boolean} [options.withoutClickHandler=false] - не перехватывать
     *   нажатия на ссылки
     * @param {boolean} [options.withoutSubmitHandler=false] - не перехватывать
     *   отправку форм
     * @param {boolean} [options.isModalNow=false] - позволяет указать,
     *   является ли текущая страница модальным окном
     * @param {number} [options.maxLifetime=3600] - максимальное время жизни
     *   страницы, при превышении которого amajaxify отключится и позволит
     *   следующему клику по ссылке перезагрузить страницу целиком
     *   (в секундах, 0 отключает данное поведение)
     * @returns {boolean}
     *
     * @method init
     */
    init: function(options) {
        options = options || {};

        if (!window.history || !window.history.pushState || !window.history.replaceState) {
            console.log('amajaxify: window.history is not supported, AJAX disabled');
            return false;
        }

        if (!options.force) {
            if (this.archiveHosts.indexOf(location.hostname.toLowerCase()) >= 0) {
                console.log('amajaxify: Wayback Machine detected, AJAX disabled');
                return false;
            }
        }

        this.state.initAt = new Date().getTime();

        // Иногда бывает надобно присылать в HTML-коде скрипты (какие-нибудь яндекс-карты, например)
        this.allowScriptTags = !!options.allowScriptTags;

        // После обновления страницы она прокручивается до верха; данная опция позволяет не делать этого,
        // если страница прокручена вниз совсем чуть-чуть
        if (options.scrollToTopFrom !== undefined && options.scrollToTopFrom !== null) {
            this.scrollToTopFrom = options.scrollToTopFrom;
        }

        if (options.maxLifetime !== undefined && options.maxLifetime !== null) {
            this.maxLifetime = options.maxLifetime;
        }

        this.customFetch = options.customFetch;

        if (options.updateModalFunc) {
            this.updateModalFunc = options.updateModalFunc;
        }

        window.addEventListener('popstate', this._popstateEvent.bind(this));
        if (window.FormData && !options.withoutSubmitHandler) {
            window.addEventListener('submit', this._submitEvent.bind(this));
        }

        // Если страница — модальное окно, но её открыли не через AJAX, а напрямую по ссылке,
        // позволяем уведомить нас об этом во время инициализации
        this.state.isModalNow = options.isModalNow || false;

        // Нужно сохранить изначальный state в истории
        this.updatePageState(null, null, this.state.isModalNow, {noScroll: true, replaceState: true});

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
            options.jQueryRef(document).on('click', 'a', this.linkClickHandler.bind(this));
        } else if (!options.withoutClickHandler) {
            document.body.addEventListener('click', this.linkClickHandler.bind(this));
        } // else - кто-то должен повесить обработчик самостоятельно

        this.state.enabled = true;
        return true;
    },


    /**
     * Инициализирован ли amajaxify.
     *
     * @returns {boolean}
     *
     * @method isEnabled
     */
    isEnabled: function() {
        return this.state.enabled;
    },


    /**
     * Является ли текущая страница модальным окном.
     *
     * @returns {boolean}
     *
     * @method isModalNow
     */
    isModalNow: function() {
        return this.state.isModalNow;
    },


    /**
     * Устанавливает новое значение минимальной прокрутки по вертикали,
     * при которой прокручивать обратно наверх после замены содержимого
     * страницы.
     *
     * @param {number} value - само значение
     */
    setScrollToTopFrom: function(value) {
        this.scrollToTopFrom = value;
    },


    /**
     * Подгружает контент страницы по ajax со всеми необходимыми действиями:
     * history.pushState, unload/load, вот это вот всё. Возвращает true, если
     * запрос отправился.
     *
     * @param {string} method - HTTP-метод для отправки запроса
     * @param {string} link - ссылка на подгружаемую страницу
     * @param body - тело HTTP-запроса (скармливается в fetch как есть)
     * @param {Object} [options] - опции, которые будут переданы в
     *   handlePageData
     * @returns {boolean}
     *
     * @method goto
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
     * Костыль для Safari и хитрых кнопок. Чтобы узнать, какую кнопку кликнули
     * для отправки формы, перехватываем событие onclick и из него вызываем
     * этот метод, который запомнит нам кликнутую кнопку, которую мы потом
     * достанем в _submitEvent.
     *
     * Если обработчик кликов отключен опцией withoutClickHandler и
     * linkClickHandler тоже никто не вызывает, вызывайте этот метод
     * самостоятельно.
     *
     * @param {HTMLElement} btn - кнопка формы
     *
     * @method handleSubmitBtnWorkaround
     */
    handleSubmitBtnWorkaround: function(btn) {
        if (
            !btn ||
            btn.tagName.toLowerCase() !== 'input' && btn.tagName.toLowerCase() !== 'button' ||
            (btn.getAttribute('type') || '').toLowerCase() != 'submit'
        ) {
            this._clickedBtn = null;
            if (this._clickedBtnTimer) {
                clearTimeout(this._clickedBtnTimer);
                this._clickedBtnTimer = null;
            }
            return;
        }
        this._clickedBtn = btn;
        this._clickedBtnTimer = setTimeout(function() {
            this._clickedBtn = null;
            this._clickedBtnTimer = null;
        }.bind(this), 100);
    },

    /**
     * Перехват кликов по любым ссылкам на странице. Если вы отключили
     * перехват опцией withoutClickHandler, можно вызывать этот метод
     * самостоятельно, передавая объект события onclick.
     *
     * @param {object} event - событие onclick
     *
     * @method linkClickHandler
     */
    linkClickHandler: function(event) {
        if (event.isDefaultPrevented !== undefined && event.isDefaultPrevented()) {
            // костыль для bootstrap/jQuery (см. init)
            return false;
        }
        if (!this.state.enabled || event.defaultPrevented) {
            return;
        }

        // Если кликнули не левую кнопку мыши, то ничего не делаем
        if ((event.which || event.button) !== 1) {
            return;
        }

        // Если клинули с какой-то зажатой клавишей, то тоже ничего не делаем
        if (event.ctrlKey || event.altKey || event.shiftKey || event.metaKey) {
            return;
        }

        // Ищем ссылку, по которой кликнули
        var target = event.target || event.srcElement;
        while (target && target.tagName.toLowerCase() != 'a' && target !== document.body) {
            if (target.tagName.toLowerCase() == 'input' || target.tagName.toLowerCase() == 'button') {
                // Отвлекаемся на костыль: вычисление кнопки, которой отправляют форму
                this.handleSubmitBtnWorkaround(target);
            }
            target = target.parentNode || parent.srcElement;
        }
        if (!target || target === document.body) {
            return;
        }

        // Проверяем, что её можно обрабатывать
        if (target.getAttribute('data-noajax') == '1') {
            return;
        }

        var href = target.href;
        var host = (location.origin || (location.protocol + '//' + location.host));

        // Если ссылка различается только якорем, то не делаем вообще ничего:
        // браузер сам обновит location.hash и прокрутит до нужного объекта,
        // а также запустит событие window.hashchange
        var h = href.indexOf('#');
        if (h > 0) {
            var currentPage = location.toString();
            if (currentPage.indexOf('#') > 0) {
                currentPage = currentPage.substring(0, currentPage.indexOf('#'));
            }
            var hrefPage = href.substring(0, h);
            if (currentPage == hrefPage) {
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

    /**
     * Обрабатывает указанные данные, обновляя страницу и вызывая события
     * unload/prepare/load.
     *
     * Формат объекта content:
     *
     *     {
     *     // при изменении этого значения в одном из запросов будет
     *     // принудительно обновлена страница при следующем клике
     *     "v": any,
     *
     *     // при наличии будет произведён переход на указанную страницу
     *     // средствами браузера без всяких ajax (текущая страница
     *     // выгрузится)
     *     "replace": "ссылка",
     *
     *     // при наличии будет немедленно отправлен ajax-запрос на указанный
     *     // адрес, а data, modal и title будут проигнорированы
     *     "redirect": "ссылка",
     *
     *     // при наличии будет отображено модальное окно, считающееся
     *     // полноценной страницей, а data проигнорирован; при его закрытии
     *     // будет изменена адресная строка
     *     "modal": "html-код",
     *
     *     // что на что заменить на странице
     *     "data": {"id элемента": "html-код" или HTMLElement, ...},
     *
     *     // элементы, которые добавить в head; будут удалены при выгрузке
     *     "head": "html-код",
     *
     *     // заголовок страницы (да, именно html-код ради &mdash; и прочего)
     *     "title": "html-код",
     *
     *     // список ссылок к скриптам, которые надобно выполнить строго один
     *     // раз (для скриптов, запускаемых при каждой перезагрузке страницы,
     *     // используйте обычный тег <script> в "data")
     *     "scripts": [{"url": "/path/to/script.js"}, ...],
     *
     *     // плюс что угодно ещё для обработки сторонними обработчиками
     *     }
     *
     * Значения `"data"` могут иметь два типа. Если это строка, то HTML-код
     * просто помещается как содержимое внутрь элемента с данным id. Если это
     * HTML-элемент, то поведение зависит от его id: если он совпадает
     * с указанным в ключе id, то старый элемент удаляется совсем и вместо
     * него помещается новый HTML-элемент; если не совпадает, то HTML-элемент
     * просто помещается внутрь старого элемента с указанным id.
     *
     * @param {string} url - ссылка на страницу, от которой это содержимое
     *   (будет запихнуто в адресную строку)
     * @param {Object} content - содержимое страницы
     * @param {Object} [options] - дополнительные опции
     * @param {boolean} [options.replaceState=false] - использовать
        replaceState вместо pushState для запихивания ссылки
     * @param {boolean} [options.noScroll=false] - не прокручивать страницу
     *   вверх независимо от значения scrollToTopFrom
     * @param {boolean} [options.hash] - какой установить location.hash после
     *   загрузки контента (игнорируется для модального окна; `#` в начале
     *   писать не надо)
     *
     * @method handlePageData
     */
    handlePageData: function(url, content, options) {
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

        var toModal = !!(content.modal && this.updateModalFunc);

        this._linkAjaxDisableIfNeeded(content);

        if (toModal) {
            // Установка модального окна
            this._dispatchEvent('amajaxify:unload', {url: url, content: content, toModal: true});

            this.updateModalFunc(content.modal);
            if (content.title) {
                this.setTitle(content.title);
            }
            this.updatePageState(url, content.title, true, options);

            this._dispatchEvent('amajaxify:load', {url: url, content: content, toModal: true});

        } else if (content.modal) {
            // Установка модального окна обломилась
            console.warn('amajaxify: server returned content for modal window, but this is not configured; ignored');

        } else {
            // Установка обычного контента страницы
            this._dispatchEvent('amajaxify:unload', {url: url, content: content, toModal: false});

            // Позволяем обработчикам пошаманить по необходимости
            var readyContent = this._prepareContent(url, content, toModal);
            if (readyContent.hasOwnProperty('noScroll')) {
                // Обработчики prepare могут запретить прокрутку, если они
                // уже сами всё сделали
                options.noScroll = readyContent.noScroll;
                delete readyContent.noScroll;
            }

            if (this.updateModalFunc) {
                this.updateModalFunc(null);
            }

            this.setHead(readyContent.head);
            if (readyContent.title) {
                this.setTitle(readyContent.title);
            }
            // После setPageData значение прокрутки скаканёт, а нам нужно получить
            // именно старое значение, так что сохраняем его в options
            options.scrollTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop;
            this.setPageData(readyContent.data);
            this.updatePageState(url, readyContent.title, false, options);

            // Запускаем скрипты (только те, которые ещё не запускались когда-то раньше)
            if (readyContent.scripts) {
                for (var i = 0; i < readyContent.scripts.length; i++) {
                    var scriptInfo = readyContent.scripts[i];
                    var s = document.createElement('script');
                    s.src = scriptInfo.url;
                    if (this.state.loadedScripts.indexOf(s.src) >= 0) {
                        continue;
                    }
                    if (scriptInfo.integrity) {
                        s.integrity = scriptInfo.integrity;
                    }
                    s.defer = true;
                    document.head.appendChild(s);
                    this.state.loadedScripts.push(s.src);
                }
            }

            this._dispatchEvent('amajaxify:load', {url: url, content: readyContent, toModal: false});
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
            if (k != 'noScroll' && content.hasOwnProperty(k)) {
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

    updatePageState: function(url, title, isModalNow, options) {
        options = options || {};

        if (title === undefined || title === null) {
            title = this.getTitle();
        }
        if (url === undefined || url === null) {
            url = location.toString();
        }

        if (options.hash && url.indexOf('#') < 0) {
            url = url + '#' + options.hash;
        }

        var state = {
            amajaxify: true,
            isModalNow: isModalNow,
            title: title
        };

        // Тут такое дело: на некоторых криво настроенных серверах
        // бэкенд через проксю не всегда может опеределить, что
        // идёт https-запрос, и в X-Request-URL пихает http-ссылку. А параноик
        // старый Safari (в котором используется полифилл к fetch) ругается на
        // несоответствие протоколов, так что для него мы его обрежем
        if (fetch.polyfill && url.indexOf('://') > 0) {
            url = url.substring(url.indexOf('://') + 1);
        }

        // Нормализуем ссылки для сравнения: https://example.com/foo/ → /foo/
        var normCurrentUrl = this._normURL(location.toString());
        var normNewUrl = this._normURL(url);

        // Вызываем replaceState вместо pushState, если:
        // 1) Нас об этом явно попросили
        var replaceState = options.replaceState;
        // 2) Ссылка другая, и при этом не создаётся модальное окно
        // (при открытии модального окна с replaceState кнопка «Назад»
        // иногда ведёт себя неправильно)
        replaceState = replaceState || normCurrentUrl === normNewUrl && (this.state.isModalNow || !isModalNow);

        if (!replaceState) {
            history.pushState(state, '', url);
        } else {
            history.replaceState(state, '', url);
        }

        this.state.isModalNow = isModalNow;

        var scrollTop = options.scrollTop;
        if (scrollTop === undefined || scrollTop === null) {
            scrollTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop;
        }
        if (!options.noScroll && !this.state.isModalNow) {
            var elem = options.hash ? document.getElementById(options.hash) : null;
            if (elem && elem.scrollIntoView) {
                elem.scrollIntoView();
            } else if (scrollTop >= this.scrollToTopFrom) {
                window.scrollTo(0, 0);
            }
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
        if (this.maxLifetime > 0 && (new Date().getTime() - this.state.initAt) > (this.maxLifetime * 1000)) {
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
                this.setTitle(event.state.title);
            }
            // FIXME: при нажатии «Вперёд» при модальном окне контент
            // не совпадает с ссылкой, но без сохранения старого location
            // не починить. Однако сохранить его не дают две вещи:
            // 1) Другие скрипты могут произвольно вызывать replaceState
            //    и pushState, в результате сохранённая версия окажется
            //    протухшей.
            // 2) Событие popstate сразу же пихает новую ссылку в историю,
            //    в результате, если было не модальное окно и «Назад»/«Вперёд»
            //    откроет модальное, если сохранять ссылку в handlePageData
            //    (который вызывается из goto, который вызывается чуть ниже)
            //    или пусть даже в самом goto, то будет ошибочна сохранена
            //    ссылка модального окна вместо ссылки страницы, из которой
            //    мы уходим и которая будет на фоне свежеоткрытого окна.
            return;
        } else if (!this.state.isModalNow && this.updateModalFunc) {
            // Но даже если мы будем загружать новую страницу, перед его
            // загрузкой надо спрятать модальное окно, которое не страница
            // (если но есть)
            this.updateModalFunc(null);
        }
        // Здесь в принципе можно организовать кэширование, но нужно ли?
        if (!this.goto('GET', location.toString(), undefined, {replaceState: true, noScroll: true})) {
            console.warn('amajaxify: failed to popstate');
        }
    },

    /**
     * Метод, отрезающий протокол и домен от ссылки. Используется
     * для их сравнения.
     */
    _normURL: function(url) {
        if (url.indexOf('://') > 0) {
            url = url.substring(url.indexOf('://') + 3);
        }
        if (url.indexOf('/') > 0) {
            url = url.substring(url.indexOf('/'));
        }
        return url;
    },

    /**
     * Метод, пытающийся выковырять актуальный input type=submit
     */
    _getSubmitButton: function(form) {
        // Простейший случай: в современных браузерах есть :focus по мышке
        // Для <input form="formid" /> за пределами формы не работает,
        // разумеется (но ниже на этот случай есть костыль)
        var submitButton = form.querySelector('input[type="submit"]:focus, button[type="submit"]:focus');
        if (!submitButton) {
            // Костыль для Safari и для кнопок за пределами формы:
            // мы, возможно, перехватили кнопку ранее в событии onclick
            // (что интересно, onclick вызывается и при нажатии Enter, когда
            // фокус на текстовом поле)
            submitButton = this._clickedBtn;
        }
        if (!submitButton) {
            // Если форму отправляют клавишей Enter и onclick нам не помог,
            // то нужно брать первую попавшуюся кнопку
            submitButton = form.querySelector('input[type="submit"], button[type="submit"]');
        }
        return submitButton;
    },

    /**
     * Перехват отправки любой формы
     */
    _submitEvent: function(event) {
        if (event.defaultPrevented) {
            return;
        }
        var form = event.target || event.srcElement;
        if (this.submitForm(form)) {
            event.preventDefault();
            return false;
        }
    },

    /**
     * Отправляет указанную форму через метод goto.
     *
     * Возвращает true при успехе.
     *
     * @param {HTMLElement} form - собственно отправляемая форма
     * @param {HTMLElement} [submitButton] - кнопка type=submit, которая
     *   запустила отправку этой формы (если известна)
     * @returns {boolean}
     *
     * @method submitForm
     */
    submitForm: function(form, submitButton) {
        if (form.getAttribute('data-noajax') == '1' || !this.state.enabled) {
            return false;
        }

        var href = form.action || location.toString();
        var host = (location.origin || (location.protocol + '//' + location.host)) + '/';
        if (href.indexOf(host) !== 0) {
            return false;
        }

        if (!window.FormData) {
            console.warn('amajaxify: cannot send ajax form because FormData is not available');
            return false;
        }

        var formData = new FormData(form);
        submitButton = submitButton || this._getSubmitButton(form);
        if (submitButton && submitButton.name) {
            formData.append(submitButton.name, submitButton.value || '');
        }

        var method = (form.method || 'GET').toUpperCase();
        if (method == 'GET') {
            if (formData.entries === undefined) {
                // Ждём реализации в других браузерах
                return false;
            }
            var started = href.indexOf('?') >= 0;
            var i, entry;
            for (i = formData.entries(); !(entry = i.next()).done;) {
                href += (started ? '&' : '?') + encodeURIComponent(entry.value[0]) + '=' + encodeURIComponent(entry.value[1]);
                started = true;
            }
        }
        return this.goto(form.method, href, method != 'GET' ? formData : undefined);
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

    getTitle: function() {
        var titleElem = document.documentElement.getElementsByTagName('title')[0];
        if (!titleElem) {
            console.warn('amajaxify: cannot find <title> element');
            return '';
        }
        return titleElem.innerHTML;
    },

    setTitle: function(titleHTML) {
        var titleElem = document.documentElement.getElementsByTagName('title')[0];
        if (!titleElem) {
            console.warn('amajaxify: cannot find <title> element');
            return false;
        }
        titleElem.innerHTML = titleHTML;
        return true;
    },

    setPageData: function(data) {
        for (var key in data) {
            if (!data.hasOwnProperty(key)) {
                continue;
            }
            var elem = document.getElementById(key);
            if (elem) {
                if (data[key] instanceof HTMLElement) {
                    // Если нам скормили HTML-элемент с тем же id, то заменяем
                    // элемент целиком; если не с тем же, то пихаем внутрь
                    // FIXME: allowScriptTags учитывать или не надо?
                    if (data[key].id === elem.id) {
                        elem.removeAttribute('id');
                        elem.innerHTML = '';
                        elem.parentNode.insertBefore(data[key], elem);
                        elem.parentNode.removeChild(elem);
                    } else {
                        elem.innerHTML = '';
                        elem.appendChild(data[key]);
                    }
                } else {
                    // Если скормили строку, то это HTML-код и просто пихаем
                    elem.innerHTML = data[key];
                    if (this.allowScriptTags) {
                        this._startElemScripts(elem);
                    }
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

export default amajaxify;
