'use strict';

/**
 * Создаёт чистилку HTML-кода.
 *
 * Объект `allowedTags` в ключах содержит названия разрешённых HTML-тегов
 * (lowercase), а в значениях — объект с разрешёнными атрибутами (ключи —
 * их имена, значения — обычно null).
 *
 * Для разрешнённого тега в качестве значения или в ключе `_process` может
 * стоять функция — тогда она вызывается и должна вернуть HTML-элемент,
 * который будет добавлен как обработанный, или null, если добавлять ничего
 * не надо. Аргументы такие:
 *
 * - `node` — элемент, который собственно нужно обработать
 * - `copyAttrs` — если значение было объектом с `_process`, а
 *   не функцией, то он передаётся тут
 *
 * Для разрешённого атрибута в качестве значения тоже может стоять функция,
 * которая должна вернуть значение атрибута или null, если атрибут добавлять
 * не надо. Аргументы такие:
 *
 * - `node` — обрабатываемый элемент
 * - `attr` — имя обрабатываемого атрибута
 *
 * Все функции при вызове имеют в качестве `this` текущий экземпляр
 * `HTMLSanitizer`, так что можно вызывать его методы и обращаться к
 * `this.current`.
 *
 * @param {object} allowedTags - информация о разрешённых тегах
 * @param {objects} [options] - дополнительные параметры
 * @param {boolean} [options.fancyNewlines=false] - если true, то некоторые
 *   HTML-теги (вроде br или p) могут быть заменены на переносы строк
 * @param {string[]} [options.skipTags] - список имён тегов (lowercase),
 *   которые будут игнорироваться целиком и полностью, в том числе
 *   пропускаться обработка их потомков
 */
var HTMLSanitizer = function(allowedTags, options) {
    // Copy options object
    this.options = {};
    for (var key in options) {
        if (!options.hasOwnProperty(key)) {
            continue;
        }
        this.options[key] = options[key];
    }

    this.root = document.createElement('div');
    this.current = this.root;
    this.stack = [];
    this.newlines = 0;
    this.newlinesCollapsed = -1;

    this.allowedTags = allowedTags;
    this.options.skipTags = this.options.skipTags || [
        'meta', 'script', 'noscript', 'style', 'link', 'embed', 'frame', 'object',
    ];
    options.fancyNewlines = !!options.fancyNewlines;
};


/**
 * Устанавливает элемент как текущий, в который будут добавляться все новые
 * элементы через push.
 */
HTMLSanitizer.prototype.pushCurrent = function(node) {
    if (node === this.current || this.stack.indexOf(node) >= 0) {
        throw new Error('This is already current or previous node!');
    }
    this.stack.push(node);
    this.current = node;
    return node;
};


/**
 * Убирает последний текущий элемент и ставит тот, который был перед ним.
 * Если текущий — корень, ничего не делает. Возвращает удалённый элемент
 * или null.
 */
HTMLSanitizer.prototype.popCurrent = function() {
    var r = null;
    if (this.stack.length > 0) {
        r = this.stack.pop();
        this.current = this.stack.length > 0 ? this.stack[this.stack.length - 1] : this.root;
    }
    return r;
};


/**
 * Устанавливает число переносов строк, которые сейчас добавлены в конце
 * вывода, но сам вывод никак не трогает. Сбрасывает схлопывание.
 */
HTMLSanitizer.prototype.setNewlines = function(n) {
    this.newlines = n > 0 ? n : 0;
    this.newlinesCollapsed = 0;
    return this.newlines;
};


/**
 * Добавляет указанное число переносов строк `\n` в вывод.
 *
 * Особый режим — схлопывание. При нём переносы строк добавляются, но
 * следующие вызовы putNewlines не будут добавлять переносы строк, пока
 * таких пропущенных переносов не наберётся `n`.
 *
 * @param {number} n - сколько переносов добавить
 * @param {boolean} [collapsed=false] - включает схлопывание
 */
HTMLSanitizer.prototype.putNewlines = function(n, collapsed) {
    if (n > 0 && this.newlines < 1 && this.current.lastChild && this.current.lastChild instanceof Text) {
        // Убираем пробелы в конце последней строки
        this.current.lastChild.textContent = this.current.lastChild.textContent.replace(/ $/, ' ');
    }

    if (n < 0) {
        n = 0;
    }

    var s = '';
    var nActual = 0;
    for (var i = 0; i < n; i++) {
        if (this.newlinesCollapsed < 0) {
            // nothing; infinity collapse
        } else if (this.newlinesCollapsed > 0) {
            this.newlinesCollapsed--;
        } else {
            s += '\n';
            nActual += 1;
        }
    }
    this.current.appendChild(document.createTextNode(s));
    this.newlines += nActual;
    if (collapsed) {
        this.newlinesCollapsed = this.newlines;
    }
    return this.newlines;
};


/**
 * Если текущее число переносов строк в выводе меньше указанного, то добавляет
 * недостающие.
 */
HTMLSanitizer.prototype.requireNewlines = function(n, collapsed) {
    if (this.newlines < n) {
        this.putNewlines(n - this.newlines, collapsed);
    }
    return this.newlines;
};

/**
 * Обрабатывает указанный кусок HTML. Возвращает корень результата
 * для удобства.
 *
 * @param {object} htmlNodes - строка с HTML-кодом или список HTML-элементов
 *   (элементы должны быть добавлены на страницу, без этого не работает
 *   getComputedStyle в хроме)
 * @param {HTMLElement} [current=null] - если указано, этот элемент будет
 *   родителем для всех обрабатываемых элементов
 */
HTMLSanitizer.prototype.push = function(htmlNodes, current) {
    if (current) {
        this.pushCurrent(current);
        this.setNewlines(0);
    }

    var parser = null;

    if (typeof htmlNodes === 'string') {
        // Всякие школьные поделки вроде Microsoft Edge пихают в HTML-код
        // какой-то хлам, обрезаем его
        // (впрочем, в Edge всё равно кодировка слетевшая)
        var f = htmlNodes.indexOf('<body');
        if (f <= 0) {
            f = htmlNodes.indexOf('<BODY');
        }
        if (f > 0) {
            htmlNodes = htmlNodes.substring(f);
        }

        parser = document.createElement('div');
        parser.id = 'html_sanitizer_' + Math.random();
        parser.style.display = 'none';
        parser.innerHTML = htmlNodes;
        document.body.appendChild(parser); // этого требует хром для работы getComputedStyle
        htmlNodes = Array.prototype.slice.call(parser.childNodes);
    }

    try {
        for (var i = 0; i < htmlNodes.length; i++) {
            this.pushNode(htmlNodes[i]);
        }
    } finally {
        if (parser && parser.parentNode) {
            parser.parentNode.removeChild(parser);
        }
        parser = null;

        if (current) {
            if (this.popCurrent() !== current) {
                console.warn('HTMLSanitizer: element stack is broken');
            }
            this.setNewlines(0);
        }
    }

    return this.root;
};


HTMLSanitizer.prototype.pushNode = function(node) {
    var cleanNode = null;

    // HTML-комментарии игнорируем
    if (node instanceof Comment) {
        return;
    }

    // В простом тексте дорабатываем пробельные символы (по умолчанию
    // браузеры вместо всех них рисуют один пробел, это и имитируем)
    // и просто добавляем в результат
    if (node instanceof Text) {
        cleanNode = node.textContent.replace(/[\r\n\t]/g, ' ');
        cleanNode = cleanNode.replace(/  +/g, ' ');

        // После переносов строк пробелы не добавляем
        if (this.newlines > 0 || this.newlinesCollapsed < 0) {
            cleanNode = cleanNode.replace(/^ +/, '');
        }

        if (cleanNode) {
            this.current.appendChild(document.createTextNode(cleanNode));
            this.setNewlines(0);
        }
        return;
    }

    // Остальное — HTML-тег
    var tag = node.tagName.toLowerCase();

    if (this.options.skipTags.indexOf(tag) >= 0) {
        return;
    }

    if (this.allowedTags.hasOwnProperty(tag)) {
        // Забираем информацию об этом теге
        var copyAttrs = this.allowedTags[tag];

        if (typeof copyAttrs === 'function') {
            // Если есть функция, делающая хитрую обработку, то просто
            // вызываем её и сами ничего не делаем
            copyAttrs.call(this, node, null);

        } else if (copyAttrs.hasOwnProperty('_process')) {
            copyAttrs._process.call(this, node, copyAttrs);

        } else {
            // Если функции нет, работаем самостоятельно
            cleanNode = document.createElement(tag);

            // Копирование разрешённых атрибутов тега
            this.copyAttributes(node, cleanNode, copyAttrs);

            // Запихиваем в результат
            this.current.appendChild(cleanNode);

            // Копируем все внутренности
            // push сделает this.setNewlines(0) сам
            this.push(Array.prototype.slice.call(node.childNodes), cleanNode);
        }

    } else {
        // Если текущий HTML-тег вообще не разрешён, то его не копируем,
        // а копируем только потомков
        this.push(Array.prototype.slice.call(node.childNodes), null);
    }
};


/**
 * Вспомогательный метод. Копирует из `node` в `cleanNode` атрибуты,
 * разрешённые в `copyAttrs`.
 */
HTMLSanitizer.prototype.copyAttributes = function(node, cleanNode, copyAttrs) {
    for (var attr in copyAttrs) {
        if (!copyAttrs.hasOwnProperty(attr)) {
            continue;
        }
        if (attr.indexOf('_') === 0) {
            continue;
        }

        // Функция-обработчик значения атрибута, которая может пошаманить что-нибудь
        // (вызывается даже при отсутствии атрибута, так как функция может его создать)
        var copyAttrFunc = copyAttrs[attr];

        var attrValue;
        if (copyAttrFunc) {
            attrValue = copyAttrFunc.call(this, node, attr);
        } else {
            attrValue = node.hasAttribute(attr) ? node.getAttribute(attr) : null;
        }

        // Если после шаманства значение атрибута получено, то ставим его
        if (attrValue !== undefined && attrValue !== null) {
            cleanNode.setAttribute(attr, attrValue);
        }
    }
};
