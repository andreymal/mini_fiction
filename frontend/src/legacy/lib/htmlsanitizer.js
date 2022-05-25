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
 * - `attr` — имя обрабатываемого атрибута
 *
 * Все функции при вызове имеют в качестве `this` текущий экземпляр
 * `HTMLSanitizer`, так что можно вызывать его методы и обращаться к
 * `this.current`.
 *
 * Дополнительные параметры для HTML-тегов:
 *
 * - `_rename` — переименовать тег в указанный (например, `i` в `em`); всё
 *   остальное обрабатывается как обычно
 *
 * - `_nonested` — массив тегов (lowercase), внутрь которых нельзя вкладывать
 *   этот тег. Если указать просто `true`, это запретит вкладывать тег сам
 *   в себя (с учётом `_rename`, если он есть). Потомки обрабатываются
 *
 * - `_nokids` — не обрабатывать детей
 *
 * - `_nocollapse` — если true, то при включенной опции collapse запрещает
 *   удалять этот тег, даже если он пуст
 *
 * `_nocollapse` действует, даже если есть произвольная функция для обработки
 * тега, остальные опции произвольный обработчик должен учитывать
 * самостоятельно.
 *
 * @param {object} allowedTags - информация о разрешённых тегах
 * @param {objects} [options] - дополнительные параметры
 * @param {boolean} [options.fancyNewlines=false] - если true, то некоторые
 *   HTML-теги (вроде br или p) могут быть заменены на переносы строк
 * @param {boolean} [options.collapse=false] - если true, то пустые элементы
 *   без потомков будут удалять из результата. Можно выключить для отдельных
 *   тегов, прописав в их опциях `_nocollapse: true`
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
    this.stackNames = []; // имена тегов в lowercase
    this.newlines = 0;
    this.newlinesCollapsed = -1;

    this.allowedTags = allowedTags;
    this.options.skipTags = this.options.skipTags || [
        'meta', 'script', 'noscript', 'style', 'link', 'embed', 'frame', 'object',
    ];
    options.fancyNewlines = !!options.fancyNewlines;
    options.collapse = !!options.collapse;
};


/**
 * Устанавливает элемент как текущий, в который будут добавляться все новые
 * элементы через push. Не добавляет его в результат; вызывающий должен
 * сделать это сам.
 */
HTMLSanitizer.prototype.pushCurrent = function(node) {
    if (node === this.current || this.stack.indexOf(node) >= 0) {
        throw new Error('This is already current or previous node!');
    }
    this.stack.push(node);
    this.stackNames.push(node.tagName.toLowerCase());
    this.current = node;
    return node;
};


/**
 * Убирает последний текущий элемент и ставит тот, который был перед ним.
 * Если текущий — корень, ничего не делает. Возвращает удалённый элемент
 * или null.
 */
HTMLSanitizer.prototype.popCurrent = function() {
    var r = null;
    if (this.stack.length > 0) {
        r = this.stack.pop();
        this.stackNames.pop();
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
 * Особый режим — схлопывание. При нём переносы строк добавляются, но
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
    if (s) {
        this.current.appendChild(document.createTextNode(s));
    }
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
 * Проверяет, есть ли тег с указанным именем в текущем стеке тегов,
 * и возвращает true, если тег действительно есть. Если передать массив,
 * то возвращает true, если будет найден любой из перечисленных тегов.
 * Используется для предотвращения вложения запрещённых тегов друг в друга
 * (например, <a> внутрь другого <a>). Название тега должно быть в нижнем
 * регистре.
 */
HTMLSanitizer.prototype.isTagInStack = function(tags) {
    if (typeof tags === "string") {
        return this.stackNames.indexOf(tags) >= 0;
    }

    for (var i = 0; i < tags.length; i++) {
        if (this.stackNames.indexOf(tags[i]) >= 0) {
            return true;
        }
    }

    return false;
}

/**
 * Обрабатывает указанный кусок HTML. Возвращает корень результата
 * для удобства.
 *
 * В атрибуте `current` можно указать элемент, который будет добавлен в стек
 * элементов и который будет родителем для всех последующих элементов.
 * При включенной опции collapse, если этот элемент был пуст, удаляет его
 * из результата.
 *
 * @param {object} htmlNodes - строка с HTML-кодом или список HTML-элементов
 *   (элементы должны быть добавлены на страницу, без этого не работает
 *   getComputedStyle в хроме)
 * @param {HTMLElement} [current=null] - если указано, этот элемент будет
 *   родителем для всех обрабатываемых элементов
 */
HTMLSanitizer.prototype.push = function(htmlNodes, current) {
    var oldNewlines, oldNewlinesCollapsed;

    if (current) {
        oldNewlines = this.newlines;
        oldNewlinesCollapsed = this.newlinesCollapsed;
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
            } else {

                // Если разрешено и элемент пустой, то удаляем его
                var r = current;
                if (r && this.options.collapse && r.parentNode) {
                    var tag = r.tagName.toLowerCase();
                    if (!this.allowedTags.hasOwnProperty(tag) || !this.allowedTags[tag]._nocollapse) {
                        if (r.childNodes.length < 1 || !r.innerHTML) {
                            r.parentNode.removeChild(r);
                            r = null;
                        }
                    }
                }

                if (r) {
                    // Если элемент не был удалён, то </тег> ну никак не является переносом строки
                    this.setNewlines(0);
                } else {
                    // Если же удалён, то возвращаем старую информацию о переносах
                    this.newlines = oldNewlines;
                    this.newlinesCollapsed = oldNewlinesCollapsed;
                }
            }
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
            this.processElement(node, copyAttrs);
        }

    } else {
        // Если текущий HTML-тег вообще не разрешён, то его не копируем,
        // а копируем только потомков
        this.push(Array.prototype.slice.call(node.childNodes), null);
    }
};


/**
 * Сравнивает указанный элемент с соседом слева и, если полностью совпадают
 * имена и атрибуты, объединяет их в один тег. Полезно для объединения
 * соседствующих strong или em. При успешном объединении возвращает новый старый
 * объединённый тег, при неуспешном ничего не делает и возвращает null.
 */
HTMLSanitizer.prototype.merge = function(node) {
    if (node.previousSibling instanceof Text && node.previousSibling.textContent) {
        // Если слева есть текст или даже просто пробелы, то объединять нельзя
        return null;
    }

    var prev = node.previousElementSibling;
    if (!prev || prev.tagName !== node.tagName) {
        // Обединяться не с чем
        return null;
    }

    if (node.attributes.length !== prev.attributes.length) {
        // Атрибуты очевидно разные, не объединяем
        return null;
    }

    // Сравниваем атрибуты
    for (var i = 0; i < node.attributes.length; i++) {
        var attr = node.attributes[i];
        if (prev.getAttribute(attr.name) !== attr.value) {
            return null;
        }
    }

    // Атрибуты совпадают — можно объединять
    var kids = Array.prototype.slice.call(node.childNodes);
    for (var i = 0; i < kids.length; i++) {
        prev.appendChild(kids[i]);
    }
    node.parentNode.removeChild(node);
    return prev;
}


/**
 * Стандартный обработчик добавления тега, срабатывающий, если не установлен
 * сторонний (через `_process`).
 */
HTMLSanitizer.prototype.processElement = function(node, copyAttrs) {
    copyAttrs = copyAttrs || {};

    // Проверяем, что этот тег можно вкладывать
    if (copyAttrs._nonested) {
        var nonested = copyAttrs._nonested === true ? [node.tagName.toLowerCase()] : copyAttrs._nonested;
        if (this.isTagInStack(nonested)) {
            // Вкладывать нельзя, обрабатываем потомков и всё
            if (!copyAttrs._nokids) {
                this.push(Array.prototype.slice.call(node.childNodes), null);
            }
            return;
        }
        // Попали сюда — значит вкладывать можно, продолжаем дальше
    }

    // Создаём копию тега. Если прописан синоним, то переименовываем
    var cleanNode = document.createElement(
        copyAttrs.hasOwnProperty('_rename') ? copyAttrs._rename : node.tagName
    );

    // Копирование разрешённых атрибутов тега
    this.copyAttributes(node, cleanNode, copyAttrs);

    // Запихиваем в результат
    this.current.appendChild(cleanNode);

    // Пробуем объединить с предыдущим тегом
    // (FIXME: это не очень оптимально, лучше объединять без создания реального
    // DOM-элемента, но для этого нужно весь код рефакторить)
    var merged = null;
    if (copyAttrs._merge) {
        merged = this.merge(cleanNode);
        if (merged !== null) {
            cleanNode = merged;
        }
    }

    // Если объединения не случилось, значит начался новый тег и нужно обновить
    // информацию о состоянии переносов строк
    if (!merged) {
        this.setNewlines(0);
    }

    // Копируем все внутренности
    if (!copyAttrs._nokids) {
        this.push(Array.prototype.slice.call(node.childNodes), cleanNode);
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

export default HTMLSanitizer;
