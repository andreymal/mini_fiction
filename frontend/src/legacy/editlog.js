'use strict';

/* global core: false */


var editlog = {
    load: function(content) {
        this.bindExpandButtons(content);
    },

    loadModal: function(modalElement) {
        this.bindExpandButtons(modalElement);
    },

    bindExpandButtons: function(dom) {
        var btns = dom.getElementsByClassName('editlog-expand-btn');
        for (var i = 0; i < btns.length; i++) {
            this.bindExpandButton(btns[i]);
        }
    },

    bindExpandButton: function(btn) {
        btn.addEventListener('click', function(event) {
            var wrap = btn.parentNode;
            if (!wrap.classList.contains('editlog-expand-btn-wrap')) {
                return;
            }
            var data = wrap.nextElementSibling;
            if (!data || !data.classList.contains('editlog-unchanged')) {
                return;
            }

            event.preventDefault();
            wrap.parentNode.removeChild(wrap);
            data.style.display = '';
            return false;
        });
    },
};

export default editlog;
