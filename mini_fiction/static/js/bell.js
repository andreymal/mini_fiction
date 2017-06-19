'use strict';

/* global core: false */


var bell = {
    _storageEventBind: null,
    _updaterInterval: null,

    load: function() {
        if (!this._storageEventBind) {
            this._storageEventBind = this._storageEvent.bind(this);
            window.addEventListener('storage', this._storageEventBind);
        }

        var link = document.getElementById('nav-icon-bell');
        if (!link) {
            if (this._updaterInterval !== null) {
                clearInterval(this._updaterInterval);
                this._updaterInterval = null;
            }
            return;
        }

        if (this._updaterInterval === null) {
            this._updaterInterval = setInterval(this.reloadUnreadCount.bind(this), 15000);
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
                bell.setViewed(data.last_id);
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
    },

    reloadUnreadCount: function(force) {
        if (!force && window.localStorage) {
            var tm = Date.now();
            if (localStorage.mfBellLastRequest && (tm - parseInt(localStorage.mfBellLastRequest, 10)) < 14000) {
                return false;
            }
            localStorage.mfBellLastRequest = tm.toString();
        }

        core.ajax.fetch('/notifications/unread_count/')
            .then(function(response) {
                return response.json();

            }).then(function(data) {
                if (!data.success) {
                    console.error(data);
                    return;
                }
                bell.setUnreadCount(data.unread_count);

            }).then(null, function(err) {
                console.error(err);
            });

        return true;
        },

    setUnreadCount: function(count, noEmit) {
        var link = document.getElementById('nav-icon-bell');
        if (!link) {
            return;
        }
        var cntitem = link.parentNode.getElementsByClassName('js-notifications-count')[0];
        if (!cntitem) {
            return;
        }

        cntitem.textContent = count.toString();
        cntitem.style.display = count > 0 ? '' : 'none';

        if (!noEmit && window.localStorage) {
            localStorage.mfBellUnreadCount = count.toString();
        }
    },

    setViewed: function(lastId) {
        if (!lastId) {
            return;
        }

        core.ajax.post('/notifications/' + lastId + '/set_viewed/')
            .then(function(response) {
                return response.json();

            }).then(function(data) {
                if (!data.success) {
                    console.error(data);
                    return;
                }
                bell.setUnreadCount(data.unread_count);

            }).then(null, function(err) {
                console.error(err);
            });
    },

    _storageEvent: function(event) {
        if (event.key != 'mfBellUnreadCount') {
            return;
        }
        if (event.newValue !== null) {
            this.setUnreadCount(parseInt(event.newValue, 10), true);
        }
    }
};


core.onload(bell.load.bind(bell));
