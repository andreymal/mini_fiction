import bold from 'images/markitup/bold.svg'
import italic from 'images/markitup/italic.svg'
import strike from 'images/markitup/strike.svg'
import underline from 'images/markitup/underline.svg'
import header from 'images/markitup/header-3.svg'
import hr from 'images/markitup/more.svg'
import center from 'images/markitup/float-center.svg'
import right from 'images/markitup/float-right.svg'
import image from 'images/markitup/image.svg'
import attachment from 'images/markitup/link.svg'
import bullet from 'images/markitup/list-bullet.svg'
import ordered from 'images/markitup/list-ordered.svg'
import item from 'images/markitup/single-item.svg'
import blockquote from 'images/markitup/blockquote.svg'
import subscript from 'images/markitup/subscript.svg'
import superscript from 'images/markitup/superscript.svg'
import code from 'images/markitup/code.svg'
import decrease from 'images/markitup/size-decrease.svg'
import background from 'images/markitup/background.svg'

export default {
    onShiftEnter: {keepDefault: false, replaceWith: '<br />\n'},
    onCtrlEnter: {keepDefault: false, openWith: '\n<p>', closeWith: '</p>\n'},
    markupSet: [
        {name: 'Жирный', key: 'B', openWith: '<strong>', closeWith: '</strong>', svg: bold},
        {name: 'Курсив', key: 'I', openWith: '<em>', closeWith: '</em>', svg: italic},
        {name: 'Зачеркнуть', key: 'S', openWith: '<s>', closeWith: '</s>', svg: strike},
        {name: 'Подчеркнуть', key: 'U', openWith: '<u>', closeWith: '</u>', svg: underline},
        {separator: ' '},
        {name: 'Подзаголовок', openWith: '<h3>', closeWith: '</h3>', svg: header},
        {name: 'Разделитель', replaceWith: '<hr>', svg: hr},
        {separator: ' '},
        {name: 'По центру', openWith: '<p align="center">', closeWith: '</p>', svg: center},
        {name: 'По правому краю', openWith: '<p align="right">', closeWith: '</p>', svg: right},
        {separator: ' '},
        {
            name: 'Добавить изображение',
            replaceWith: '<img src="[![' + 'Введите адрес изображения:' + ':!:https://]!]" />',
            svg: image
        },
        {
            name: 'Добавить ссылку',
            key: 'L',
            openWith: '<a href="[![' + 'Адрес ссылки:' + ':!:https://]!]"(!( title="[![Title]!]")!)>',
            closeWith: '</a>',
            placeHolder: 'Название ссылки',
            svg: attachment
        },
        {separator: ' '},
        {
            name: 'Обычный список',
            openWith: '<li>',
            closeWith: '</li>',
            multiline: true,
            openBlockWith: '<ul>\n',
            closeBlockWith: '\n</ul>',
            svg: bullet
        },
        {
            name: 'Нумерованный список',
            openWith: '<li>',
            closeWith: '</li>',
            multiline: true,
            openBlockWith: '<ol>\n',
            closeBlockWith: '\n</ol>',
            svg: ordered
        },
        {name: 'Элемент списка', openWith: '<li>', closeWith: '</li>', svg: item},
        {separator: ' '},
        {
            name: 'Цитировать', key: 'Q', replaceWith: function (m) {
                if (m.selectionOuter) return '<blockquote>' + m.selectionOuter + '</blockquote>'; else if (m.selection) return '<blockquote>' + m.selection + '</blockquote>'; else return '<blockquote></blockquote>'
            }, svg: blockquote
        },
        {name: 'Верхний индекс', openWith: '<sup>', closeWith: '</sup>', svg: superscript},
        {name: 'Нижний индекс', openWith: '<sub>', closeWith: '</sub>', svg: subscript},
        {name: 'Код', openWith: '<pre>', closeWith: '</pre>', svg: code},
        {name: 'Уменьшить размер', openWith: '<small>', closeWith: '</small>', svg: decrease},
        {name: 'Lite-спойлер', openWith: '<span class="spoiler-gray">', closeWith: '</span>', svg: background},
    ]
};
