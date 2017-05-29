'use strict';

/* global core: false, $: false, mySettings: false */


var common = {
    menuState: false,
    subforms: [],
    _subformSubmitBinded: null,

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
        $('.with-markitup', elem).markItUp(mySettings);
    },

    markitupDestroy: function(elem) {
        $('.with-markitup', elem).markItUpRemove();
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
    }
};


core.oninit(common.init.bind(common));
core.onload(common.load.bind(common));
core.onunload(common.unload.bind(common));
core.onloadModal(common.loadModal.bind(common));
core.onunloadModal(common.unloadModal.bind(common));
