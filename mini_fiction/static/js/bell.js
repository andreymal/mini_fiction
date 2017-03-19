'use strict';

/* global core: false */


var bell = {
    load: function() {
        var link = document.getElementById('nav-icon-bell');
        if (!link) {
            return;
        }
        link.addEventListener('click', function(event) {
            if (window.innerWidth <= 640) {
                return; // На узких экранах просто открываем страницу с уведомлениями
            }
            bell.togglePopup();
            event.preventDefault();
            return false;
        });
    },

    togglePopup: function() {
        var popup = document.getElementById('bell-popup');
        if (popup.style.display != 'none') {
            this.hidePopup();
        } else {
            this.loadPopup();
        }
    },

    loadPopup: function() {
        var link = document.getElementById('nav-icon-bell');
        var popup = document.getElementById('bell-popup');
        var content = document.getElementById('bell-popup-content');
        var url = link.getAttribute('data-ajax');

        popup.style.display = '';
        link.parentNode.classList.add('active');

        core.ajax.fetch(url)
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (core.handleResponse(data, url)) {
                    bell.hidePopup();
                    return;
                }
                content.innerHTML = data.popup;
            }).then(null, function(exc) {
                bell.hidePopup();
                core.handleError(exc);
            });

        content.innerHTML = '';
    },

    hidePopup: function() {
        var link = document.getElementById('nav-icon-bell');
        var popup = document.getElementById('bell-popup');
        popup.style.display = 'none';
        link.parentNode.classList.remove('active');
    }
};


core.onload(bell.load.bind(bell));
