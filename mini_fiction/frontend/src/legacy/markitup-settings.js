export default {
    onShiftEnter:   {keepDefault: false, replaceWith: '<br />\n'},
    onCtrlEnter:    {keepDefault: false, openWith: '\n<p>', closeWith: '</p>\n'},
    markupSet: [
        {name: 'Жирный', className:'edit-bold', key:'B', openWith:'<strong>', closeWith:'</strong>'},
        {name: 'Курсив', className:'edit-italic', key:'I', openWith:'<em>', closeWith:'</em>'},
        {name: 'Зачеркнуть', className:'edit-strike', key:'S', openWith:'<s>', closeWith:'</s>'},
        {name: 'Подчеркнуть', className:'edit-underline', key:'U', openWith:'<u>', closeWith:'</u>'},
        {separator: '---------------'},
        {name: 'Подзаголовок', className:'edit-h', openWith:'<h3>', closeWith:'</h3>'},
        {name: 'Разделитель', className:'edit-hr', replaceWith:'<hr>'},
        {separator: '---------------'},
        {name: 'По центру', className:'edit-alignment-center', openWith:'<p align="center">', closeWith:'</p>'},
        {name: 'По правому краю', className:'edit-alignment-right', openWith:'<p align="right">', closeWith:'</p>'},
        {separator: '---------------'},
        {name: 'Добавить изображение', className:'edit-image', replaceWith:'<img src="[!['+'Введите адрес изображения:'+':!:http://]!]" />' },
        {name: 'Добавить ссылку', className:'edit-anchor', key:'L', openWith:'<a href="[!['+'Введите url адрес:'+':!:http://]!]"(!( title="[![Title]!]")!)>', closeWith:'</a>', placeHolder:'Введите адрес ссылки...' },
        {separator: '---------------'},
        {name: 'Обычный список', className:'edit-list', openWith:'<li>', closeWith:'</li>', multiline: true, openBlockWith:'<ul>\n', closeBlockWith:'\n</ul>' },
        {name: 'Нумерованный список', className:'edit-list-order', openWith:'<li>', closeWith:'</li>', multiline: true, openBlockWith:'<ol>\n', closeBlockWith:'\n</ol>' },
        {name: 'Элемент списка', className:'edit-list-item', openWith:'<li>', closeWith:'</li>'},
        {separator: '---------------'},
        {name: 'Цитировать', className:'edit-quotation', key:'Q', replaceWith: function(m) { if (m.selectionOuter) return '<blockquote>'+m.selectionOuter+'</blockquote>'; else if (m.selection) return '<blockquote>'+m.selection+'</blockquote>'; else return '<blockquote></blockquote>'}},
        {name: 'Верхний индекс', className:'edit-superscript', openWith:'<sup>', closeWith:'</sup>'},
        {name: 'Нижний индекс', className:'edit-subscript', openWith:'<sub>', closeWith:'</sub>'},
        {name: 'Код', className:'edit-code', openWith: '<pre>', closeWith:'</pre>'},
        {name: 'Уменьшить размер', className:'edit-small', openWith:'<small>', closeWith:'</small>'},
        {name: 'Lite-спойлер', className:'edit-spoiler-gray', openWith:'<span class="spoiler-gray">', closeWith:'</span>'},
        {separator: '---------------'},
        {name: 'Конвертация c фикбука', className:'edit-ficbook', replaceWith: function(markitup) {
            markitup.textarea.value = markitup.textarea.value
                .replace(/<center>\s*\*+\s*\*+\s*\*+\s*<\/center>/g, '<hr>')
                .replace(/<center>/g, '<p align="center">')
                .replace(/<\/center>/g, '</p>')
                .replace(/<right>/g, '<p align="right">')
                .replace(/<\/right>/g, '</p>')
                .replace(/<i>/g, '<em>')
                .replace(/<\/i>/g, '</em>')
                .replace(/<b>/g, '<strong>')
                .replace(/<\/b>/g, '</strong>')
                .replace(/<tab>/g, '\n\n')
                .replace(/\n{2,}/g, '\n\n')
                .replace(/\n\n\s*/g, '\n\n');
            }},
    ]
};
