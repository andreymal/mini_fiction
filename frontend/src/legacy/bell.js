import core from './core';
import { post, get } from '../utils/ajax';

'use strict';

var bell = {
    _storageEventBind: null,
    _updaterInterval: null,
    _lastError: null,

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
        var contentLoading = document.getElementById('bell-popup-content-loading');
        var url = link.getAttribute('data-ajax');

        popup.style.display = '';
        link.parentNode.classList.add('active');

        get(url)
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.popup) {
                    content.innerHTML = data.popup;
                }
                if (core.handleResponse(data, url)) {
                    bell.hidePopup();
                    return;
                } else if (data.success && data.last_id) {
                    bell.setViewed(data.last_id);
                }
            }).then(null, function(exc) {
                bell.hidePopup();
                core.handleError(exc);
            }).then(function() {
                content.style.display = '';
                contentLoading.style.display = 'none';
            });

        content.style.display = 'none';
        contentLoading.style.display = '';
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

        get('/notifications/unread_count/')
            .then(function(response) {
                if (response.status < 100 || response.status >= 400) {
                    return {success: false, error: 'Bell fetch error ' + response.status};
                }
                return response.json();

            }).then(function(data) {
                if (!data.success) {
                    bell._lastError = data;
                    console.error(data);
                    return;
                }
                if (bell._lastError) {
                    console.log('Bell is working now');
                    bell._lastError = null;
                }
                bell.setUnreadCount(data.unread_count);

            }).then(null, function(err) {
                bell._lastError = err;
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

        post('/notifications/' + lastId + '/set_viewed/')
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

export default bell;
