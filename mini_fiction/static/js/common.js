'use strict';

/* global core: false, $: false, mySettings: false */


var common = {
    menuState: false,
    subforms: [],
    _subformSubmitBinded: null,
    _pasteEvents: [],

    allowedTags: null,

    init: function() {
        // Кнопка закрытия новости, если таковая присутствует
        var btn = document.getElementById('close-shown-newsitem');
        if (btn) {
            btn.addEventListener('click', function() {
                var expiration_date = new Date();
                expiration_date.setFullYear(expiration_date.getFullYear() + 10);
                document.cookie = 'last_newsitem=' + parseInt(btn.getAttribute('data-id')) + '; path=/; expires=' + expiration_date.toGMTString();
            });
        }

        // Кнопка закрытия уведомления об отсутствующей почте
        var nbtn = document.getElementById('close-email-notice');
        if (nbtn && document.cookie.indexOf('hide_email_notice=1') >= 0) {
            nbtn.parentNode.parentNode.removeChild(nbtn.parentNode);
            nbtn = null;
        } else if (nbtn) {
            nbtn.addEventListener('click', function() {
                document.cookie = 'hide_email_notice=1; path=/; expires=';
            });
        }

        this._subformSubmitBinded = this._subformSubmitEvent.bind(this);
    },

    load: function(content) {
        this.bindContactsAdd();
        this.markitupFor(content);
        this.buttonsFor(content);
        this.bootstrapFor(content);

        // Переключение мобильного меню
        document.getElementById('mobile-menu-btn').addEventListener('click', function(event) {
            var l = document.getElementById('nav-main-links');
            l.classList.toggle('shown');
            common.menuState = l.classList.contains('shown');
            event.preventDefault();
            return false;
        });

        if (this.menuState) {
            document.getElementById('nav-main-links').classList.add('shown');
        }

        // Переключение меню профиля
        var profileMenuHeader = document.getElementById('nav-profile-menu-header');
        if (profileMenuHeader) {
            profileMenuHeader.addEventListener('click', function(event) {
                var l = document.getElementById('nav-profile-menu-content');
                l.classList.toggle('shown');
                common.profileMenuState = l.classList.contains('shown');
                event.preventDefault();
                return false;
            });
        }

        // Формы подписки
        var subforms = document.getElementsByClassName('js-subscription-form');
        for (var i = 0; i < subforms.length; i++) {
            this.initSubscriptionForm(subforms[i]);
            this.subforms.push(subforms[i]);
        }
    },

    loadModal: function(content) {
        this.markitupFor(content);
        this.buttonsFor(content);
        this.bootstrapFor(content);
    },

    unload: function(content) {
        for (var i = this.subforms.length - 1; i >= 0; i--) {
            this.destroySubscriptionForm(this.subforms[i]);
        }
        this.subforms = [];
        this.markitupDestroy(content);
    },

    unloadModal: function(content) {
        this.markitupDestroy(content);
    },

    initSubscriptionForm: function(form) {
        form.addEventListener('submit', this._subformSubmitBinded);
        var inputs = form.getElementsByTagName('input');
        for (var i = 0; i < inputs.length; i++) {
            inputs[i].addEventListener('change', this._subformSubmitBinded);
        }
        var btn = form.getElementsByClassName('js-subscription-form-submit')[0];
        if (btn) {
            btn.style.display = 'none';
        }
    },

    destroySubscriptionForm: function(form) {
        var btn = form.getElementsByClassName('js-subscription-form-submit')[0];
        if (btn) {
            btn.style.display = '';
        }
        var inputs = form.getElementsByTagName('input');
        for (var i = 0; i < inputs.length; i++) {
            inputs[i].removeEventListener('change', this._subformSubmitBinded);
        }
        form.removeEventListener('submit', this._subformSubmitBinded);
    },

    _subformSubmitEvent: function(event) {
        var form = event.target;
        if (form.tagName.toLowerCase() != 'form') {
            form = form.form;
        }
        event.preventDefault();

        var data = new FormData(form);
        data.append('short', '1');

        core.ajax.post(form.action, data)
            .then(function(response) {
                return response.json();

            }).then(function(data) {
                if (core.handleResponse(data, form.action)) {
                    return;
                }
                core.notify('Изменение подписки прошло успешно');

            }).then(null, function(err) {
                console.error(err);
                core.notifyError(err);
            });

        return false;
    },

    bindContactsAdd: function() {
        // Виджет редактирования контактов
        core.bind('.contacts-add', 'click', this._addContactEvent);
    },

    markitupFor: function(elem) {
        // Собственно markitup
        $('.with-markitup', elem).markItUp(mySettings);

        // Обработка вставки HTML-кода из буфера обмена
        var e = this._pasteEvent.bind(this);

        var areas = elem.getElementsByClassName('with-markitup');
        for (var i = 0; i < areas.length; i++) {
            areas[i].addEventListener('paste', e);
            this._pasteEvents.push([areas[i], e]);
        }
    },

    markitupDestroy: function(elem) {
        $('.with-markitup', elem).markItUpRemove();

        // Если у поля ввода был обработчик вставки, то отключаем его
        var areas = elem.getElementsByClassName('with-markitup');
        for (var i = 0; i < areas.length; i++) {
            var eventPos = null;
            for (var j = 0; j < this._pasteEvents.length; j++) {
                if (this._pasteEvents[j][0] === areas[i]) {
                    eventPos = j;
                    break;
                }
            }

            if (eventPos !== null) {
                this._pasteEvents[eventPos][0].removeEventListener('paste', this._pasteEvents[eventPos][1]);
                this._pasteEvents.splice(eventPos, 1);
            }
        }
    },

    bootstrapFor: function(elem) {
        $('.bootstrap', elem).each(this.bootstrap);
    },

    buttonsFor: function(elem) {
        // Виджет выбора персонажей
        $('.characters-select:checked + img', elem).addClass('ui-selected');
        $(".character-item", elem).click(function() {
            var input = $('input', this);
            var typ = input.attr('type');
            var checked;
            if (typ == 'checkbox') {
                checked = input.prop('checked');
                input.prop('checked', !checked);
                $('img', this).toggleClass('ui-selected', !checked);

            } else if (typ == 'radio') {
                var oldInput = input[0].form.querySelector('input[name="' + input.attr('name') + '"]:checked');
                if (oldInput) {
                    $('img', oldInput.parentNode).toggleClass('ui-selected', false);
                }
                checked = input.prop('checked');
                input.prop('checked', !checked);
                $('img', this).toggleClass('ui-selected', !checked);

            } else {
                throw new Error('Unsupported input type ' + typ);
            }
        });
    },

    bootstrap: function() {
        var group = $(this);
        var buttons_container = $('.buttons-visible', group);
        var data_container = $('.buttons-data', group);
        var type = group.hasClass('checkbox') ? 'checkbox' : 'radio';

        // Обработка проставленных заранее чекбоксов и радиоселектов
        $('input', data_container).each(function() {
            var input = $(this);
            var value = input.attr('value');
            if (input.prop('checked')) {
                $('button[value=' + value + ']', buttons_container).addClass('active');
            }
        });
        // Onclick-обработчик
        $('button', buttons_container).each(function() {
            var button = $(this);
            button.on('click', function() {
                var value = button.attr('value');
                if (type == 'checkbox') {
                    var input = $('input:checkbox[value=' + value + ']', data_container);
                    input.prop('checked', !($('input:checked[value=' + value + ']', data_container).length | 0));
                } else if (type == 'radio') {
                    if (!(!!($('input:radio[value=' + value + ']', data_container).prop('checked')))) {
                        $('input:radio', data_container).prop('checked', false);
                        $('input:radio[value=' + value + ']', data_container).prop('checked', true);
                    }
                }
            });
        });
    },

    /**
     * Вставляет указанный HTML-код, прогнав его через sanitizeHTML,
     * в textarea в то место, где сейчас находится курсор.
     */
    pasteHTML: function(textarea, html) {
        var container = document.createElement('div');

        // Всякие школьные поделки вроде Microsoft Edge пихают в HTML-код
        // какой-то хлам, обрезаем его
        // (впрочем, в Edge всё равно кодировка слетевшая)
        var f = html.indexOf('<body');
        if (f <= 0) {
            f = html.indexOf('<BODY');
        }
        if (f > 0) {
            html = html.substring(f);
        }

        common.sanitizeHTML(container, html, {
            fancyNewlines: true,
            allowedTags: common.allowedTags,
            tabunAlign: false,
        });

        var result = container.innerHTML.trim();

        if (document.selection) {
            // IE
            textarea.focus();
            var sel = document.selection.createRange();
            sel.text = result;
        } else if (textarea.selectionStart || textarea.selectionStart == '0') {
            // non-IE
            var startPos = textarea.selectionStart;
            var endPos = textarea.selectionEnd;
            textarea.value = textarea.value.substring(0, startPos) + result + textarea.value.substring(endPos);
            textarea.selectionStart = startPos + result.length;
            textarea.selectionEnd = startPos + result.length;
        } else {
            textarea.value += textarea;
        }
    },

    /**
     * Преобразует произвольный HTML-код в другой HTML-код согласно указанным
     * опциям.
     *
     * Для конвертирования тегов их необходимо разрешить, указав в объекте
     * `options.allowedTags`. Его ключами должны являться названия тегов
     * в нижнем регистре, а значениями объект с разрешёнными атрибутами.
     *
     * Объект с разрешёнными атрибутами в ключах должен содержать название
     * атрибута, а в значениях — null (тогда атрибут копируется как есть, если
     * имеется) или функция. Если указана функция, то при обработке атрибута
     * она вызывается с параметрами `(attrValue, attrName, node, options)`.
     * Если атрибут отсутствует, то attrValue установлено в null. Функция
     * должна вернуть значение атрибута, которое будет установлено. Если
     * возвращается null или undefined, то атрибут пропускается.
     *
     * Специальный опциональный ключ `_node` позволяет задать функцию, которая
     * обработает текущий HTML-элемент произвольно. При её наличии она
     * вызывается с `(parent, node, copyAttrs, options)` (где `copyAttrs` —
     * словарь с разрешёнными атрибутами, который и содержит вызываемую
     * функцию `_node`) и производит всю обработку самостоятельно; ни
     * обработка атрибутов, ни добавление потомков не будет произведено
     * автоматически.
     *
     * Весь объект `options` передаётся всем обработчикам как есть и может
     * содержать, помимо `allowedTags`, любые произвольные объекты.
     *
     * Имейте в виду, что данная разрабатывалась только для удобства
     * пользователей и не гарантирует защиту от XSS и прочую безопасность.
     *
     * @param {HTMLElement} parent - элемент, в который пихать результат
     * @param {object} htmlNodes - строка с HTML-кодом или массив элементов
     *   для обработки
     * @param {object} [options=null] - дополнительные опции
     */
    sanitizeHTML: function (parent, htmlNodes, options) {
        options = options || {};
        var allowedTags = options.allowedTags || {};

        var parser = null;

        if (typeof htmlNodes === 'string') {
            parser = document.createElement('div');
            parser.style.display = 'none';
            parser.innerHTML = htmlNodes;
            document.body.appendChild(parser); // этого требует хром
            htmlNodes = Array.prototype.slice.call(parser.childNodes);
        } else if (htmlNodes instanceof HTMLElement || htmlNodes instanceof Text) {
            htmlNodes = [htmlNodes];
        }

        try {
            for (var i = 0; i < htmlNodes.length; i++) {
                var node = htmlNodes[i];
                var cleanNode = null;

                if (node instanceof Comment) {
                    continue;
                }

                if (node instanceof Text) {
                    cleanNode = node.textContent.replace(/[\r\n\t]/g, ' ');
                    cleanNode = cleanNode.replace(/  +/g, ' ');
                    if (cleanNode) {
                        parent.appendChild(document.createTextNode(cleanNode));
                    }
                    continue;
                }

                var tag = node.tagName.toLowerCase();

                if (tag == 'meta' || tag == 'script' || tag == 'noscript' || tag == 'style' || tag == 'link') {
                    // nothing

                } else if (allowedTags.hasOwnProperty(tag)) {
                    // Копирование разрешённых тегов
                    var copyAttrs = allowedTags[tag];

                    cleanNode = document.createElement(tag);

                    if (copyAttrs.hasOwnProperty('_node')) {
                        // Если есть функция, делающая хитрую обработку, то просто
                        // вызываем её и сами ничего не делаем
                        copyAttrs._node(parent, node, copyAttrs, options);

                    } else {
                        // Копирование разрешённых атрибутов тега
                        for (var attr in copyAttrs) {
                            if (!copyAttrs.hasOwnProperty(attr)) {
                                continue;
                            }

                            // Функция-обработчик значения атрибута, которая может пошаманить что-нибудь
                            // (вызывается даже при отсутствии атрибута, такак функция может его создать)
                            var copyAttrFunc = copyAttrs[attr];
                            var attrValue = node.hasAttribute(attr) ? node.getAttribute(attr) : null;
                            if (copyAttrFunc) {
                                attrValue = copyAttrFunc(attrValue, attr, node, options);
                            }

                            // Если после шаманства значение атрибута получено, то ставим его
                            if (attrValue !== undefined && attrValue !== null) {
                                cleanNode.setAttribute(attr, attrValue);
                            }
                        }

                        // Копируем все внутренности
                        common.sanitizeHTML(cleanNode, Array.prototype.slice.call(node.childNodes), options);
                        parent.appendChild(cleanNode);
                    }

                } else {
                    common.sanitizeHTML(parent, Array.prototype.slice.call(node.childNodes), options);
                }
            }

        } finally {
            if (parser && parser.parentNode) {
                parser.parentNode.removeChild(parser);
            }
        }
    },

    _addContactEvent: function(event) {
        var newId = (this.parentNode.children.length - 1).toString();
        var newItem = this.previousElementSibling.cloneNode(true);

        var nameField = newItem.querySelector('select');
        nameField.name = 'contacts-' + newId + '-name';
        nameField.id = nameField.name;
        nameField.value = nameField.querySelector('option').value;

        var valueField = newItem.querySelector('input');
        valueField.name = 'contacts-' + newId + '-value';
        valueField.id = valueField.name;
        valueField.value = '';

        this.parentNode.insertBefore(newItem, this);
        event.preventDefault();
        return false;
    },

    _pasteEvent: function(event) {
        // Проверяем, что браузер правда умеет в буфер обмена
        if (!event.clipboardData || !event.clipboardData || !event.clipboardData.types || !event.clipboardData.getData) {
            return;
        }

        // Проверяем, что браузер поддерживает нужные фичи для обработки HTML-кода
        if (!String.prototype.trim || !window.getComputedStyle) {
            return;
        }

        try {
            // Если в буфере есть text/html, достаём его и обрабатываем;
            // при успехе отменяем браузерную обработку вставки
            var types = event.clipboardData.types;
            if (
                ((types instanceof DOMStringList) && types.contains("text/html")) ||
                (types.indexOf && types.indexOf('text/html') !== -1)
            ) {
                var html = event.clipboardData.getData('text/html');
                if (!html.trim()) {
                    return;
                }
                common.pasteHTML(event.target, html);
                event.stopPropagation();
                event.preventDefault();
                return false;
            }
        } catch (e) {
            console.error(e);
            alert('Paste fail: ' + e);
        }
    }
};


// Настройки для конвертера HTML-кода, вставленного из буфера обмена,
// в HTML-код, пригодный для сайта
common.allowedTags = {
    b: {}, strong: {}, i: {}, em: {}, s: {}, u: {},
    p: {},
    h3: {}, h4: {}, h5: {},
    span: {}, br: {}, hr: {}, // TODO: footnote?
    img: {src: null, alt: null, title: null},
    a: {href: null, rel: null, title: null, target: null},
    ul: {}, ol: {}, li: {},
    blockquote: {}, sup: {}, sub: {}, pre: {}, small: {}, tt: {},
};


// Конвертирование тега <p> хитрое, так как вместо него нам нужны пустые
// строки, ну и ещё атрибут align попутно
common.allowedTags.p._node = function(parent, node, copyAttrs, options) {
    var cleanNode = null;

    // Копируем один разрешённый атрибут
    var align = null;
    var attrAlign = node.getAttribute('align') || getComputedStyle(node).textAlign;
    if (attrAlign == 'left' || attrAlign == 'start') {
        align = null;  // nothing
    } else if (attrAlign == 'right' || attrAlign == 'end') {
        align = 'right';
    } else if (attrAlign == 'center') {
        align = 'center';
    }

    if (!align && options.fancyNewlines) {
        // При fancyNewlines вместо <p></p> разделяем параграфы пустой строкой
        var newline = '\n\n';
        if (parent.lastChild && parent.lastChild instanceof Text) {
            if (parent.lastChild.textContent.endsWith('\n\n')) {
                newline = '';
            } else if (parent.lastChild.textContent.endsWith('\n')) {
                newline = '\n';
            }
        }
        if (!parent.lastChild) {
            newline = '';
        }
        if (newline) {
            parent.appendChild(document.createTextNode(newline));
        }

        common.sanitizeHTML(parent, Array.prototype.slice.call(node.childNodes), options);

    } else {
        // Иначе создаём <p> как обычно
        // (за исключением случая, когда нужно выравнивание для табуна)
        if (options.tabunAlign) {
            cleanNode = document.createElement('span');
            if (align) {
                cleanNode.className = 'h-' + align;
            }
        } else {
            cleanNode = document.createElement('p');
            if (align) {
                cleanNode.setAttribute('align', align);
            }
        }
        common.sanitizeHTML(cleanNode, Array.prototype.slice.call(node.childNodes), options);
        if (options.fancyNewlines) {
            parent.appendChild(document.createTextNode('\n'));
        }
        parent.appendChild(cleanNode);
        if (options.fancyNewlines) {
            parent.appendChild(document.createTextNode('\n'));
        }
    }
};


common.allowedTags.br._node = function(parent, node, copyAttrs, options) {
    // После </p> дополнительный перенос строки не ставим
    if (parent.lastChild && parent.lastChild instanceof HTMLElement && parent.lastChild.tagName.toLowerCase() == 'p') {
        return;
    }

    if (options.fancyNewlines) {
        parent.appendChild(document.createTextNode('\n'));
    } else {
        parent.appendChild(document.createElement('br'));
    }
};


common.allowedTags.span._node = function(parent, node, copyAttrs, options) {
    // Всякие гуглодоки вместо HTML-тегов юзают span со стилями, здесь вот
    // конвертируем эти стили в HTML-теги
    var cont = parent;
    var cont2;
    var style = getComputedStyle(node);

    // font-weight → <strong>
    var bolds = ['bold', 'bolder', '500', '600', '700', '800', '900'];
    if (bolds.indexOf(style.fontWeight) >= 0) {
        cont2 = document.createElement('strong');
        cont.appendChild(cont2);
        cont = cont2;
    }

    // font-style → <em>
    var italics = ['italic', 'oblique'];
    if (italics.indexOf(style.fontStyle) >= 0) {
        cont2 = document.createElement('em');
        cont.appendChild(cont2);
        cont = cont2;
    }

    var decor = style.textDecorationLine || style.textDecoration || '';
    decor = decor.split(' ');

    // text-decoration: underline → <u>
    // Но только если родитель не ссылка
    if (decor.indexOf('underline') >= 0) {
        if (!node.parentNode || node.parentNode.tagName.toLowerCase() != 'a') {
            cont2 = document.createElement('u');
            cont.appendChild(cont2);
            cont = cont2;
        }
    }

    // text-decoration: line-through → <s>
    if (decor.indexOf('line-through') >= 0) {
        cont2 = document.createElement('s');
        cont.appendChild(cont2);
        cont = cont2;
    }

    // vertical-align: super → <sup>
    if (style.verticalAlign == 'super') {
        cont2 = document.createElement('sup');
        cont.appendChild(cont2);
        cont = cont2;
    }

    // vertical-align: sub → <sub>
    if (style.verticalAlign == 'sub') {
        cont2 = document.createElement('sub');
        cont.appendChild(cont2);
        cont = cont2;
    }

    common.sanitizeHTML(cont, Array.prototype.slice.call(node.childNodes), options);
};


common.allowedTags.b._node = function(parent, node, copyAttrs, options) {
    var cont;

    var style = getComputedStyle(node);

    var bolds = ['bold', 'bolder', '500', '600', '700', '800', '900'];
    if (style.fontWeight && bolds.indexOf(style.fontWeight) >= 0) {
        cont = document.createElement('strong');
    } else {
        // Да, так бывает! Google Docs идиот
        cont = parent;
    }

    common.sanitizeHTML(cont, Array.prototype.slice.call(node.childNodes), options);
};


common.allowedTags.img.width = common.allowedTags.img.height = function(value, attr, node) {
    // Если у картинки нет атрибута width/height, то берём CSS width/height
    if (!value) {
        value = getComputedStyle(node)[attr];
        if (!value || !value.endsWith('px')) {
            return null;
        }
        value = value.substring(0, value.length - 2);
    }

    value = parseFloat(value);
    if (!value || isNaN(value) || value <= 0.0) {
        return null;
    }
    return value;
};


core.oninit(common.init.bind(common));
core.onload(common.load.bind(common));
core.onunload(common.unload.bind(common));
core.onloadModal(common.loadModal.bind(common));
core.onunloadModal(common.unloadModal.bind(common));
