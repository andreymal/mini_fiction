'use strict';

core.define('bell', {
    load: function() {
        var link = document.getElementById('nav-icon-bell');
        link.addEventListener('click', function(event) {
            if (window.innerWidth <= 640) {
                return;
            }
            core.bell.togglePopup();
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
        var url = link.dataset.ajax;

        popup.style.display = '';
        link.parentNode.classList.add('active');

        core.ajax.fetch(url)
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (core.handleResponse(data, url)) {
                    core.bell.hidePopup();
                    return;
                }
                content.innerHTML = data.popup;
            }).catch(core.handleError);

        content.innerHTML = '';
    },

    hidePopup: function() {
        var link = document.getElementById('nav-icon-bell');
        var popup = document.getElementById('bell-popup');
        popup.style.display = 'none';
        link.parentNode.classList.remove('active');
    }
});
