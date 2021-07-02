'use strict';

import Hypher from 'hypher';
import ruHyphenation from 'hyphenation.ru';

import amajaxify from './lib/amajaxify';
import core from './core';
import common from './common';
import { post } from '../utils/ajax';
import { notify, notifyError } from '../utils/notifications';

let hypher;


/**
 * (This method is created by andreymal)
 *
 * Recursively hyphenates a array of DOM nodes.
 *
 * @param {Hypher} hyphenator
 * @param {object} nodes - DOM node or list of DOM nodes (text or elements)
 */
const hyphenateDOM = (hyphenator, nodes) => {
  if ((nodes instanceof HTMLElement) || (nodes instanceof Text)) {
    nodes = [nodes];
  }
  nodes.forEach(node => {
    if (node.nodeType === document.TEXT_NODE) {
      node.nodeValue = hyphenator.hyphenateText(node.nodeValue);
    } else if (node.childNodes && node.childNodes.length > 0) {
      hyphenateDOM(hyphenator, [...node.childNodes]);
    }
  });
};

/* global core: false, $: false, Hypher: false, common: false */


var story = {
    panel: null,
    contributorsForm: null,
    _contributorsSendEventBinded: null,
    _contributorsChangeEventBinded: null,
    _hashChangeEventBinded: null,
    _moreTagsLinks: [],

    _lsFormattingKey: 'formatting',
    _preview: {
        btn: null,
        btnEvent: null,
        selectedBtn: null,
        // selectedBtnEvent: null,

        area: null,

        textInput: null,
        textInputSelectEvent: null,
        selection: null,
    },

    _formatting: {
        form: null,
        visible: false,
        bodyClickEvent: null,
        current: {
            font: null,
            align: null,
            size: null,
            hyphens: null,
            paragraph: null
        },
    },

    init: function() {
        // Обработка нажатия кнопок голосования за рассказ
        core.utils.addLiveClickListener('js-vote-button', this._voteButtonClickEvent.bind(this));

        this.initStoryFormatting();
    },

    load: function() {
        this.panelStuff();
        this.chapterPreviewStuff();
        this.chapterLinterStuff();

        // Применяем форматирование глав
        // (из localStorage, чтобы синхронизироваться с изменениями в соседних вкладках)
        this.applyFormattingFromLocalStorage();

        // Обработчики для кнопок работы с рассказом

        // Публикация
        core.bind('#content .js-story-publish-btn', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            if (this.classList.contains('loading')) {
                return;
            }
            var url = this.href;
            post(url, undefined, [['X-AJAX', '1']])
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setPublished(response.story_id, response.published);
                    if (response.modal) {
                        core.modal(response.modal);
                    }
                }).then(null, core.handleError).then(function() {
                    this.classList.remove('loading');
                }.bind(this));
            this.classList.add('loading');
        });

        // Публикация главы
        core.bind('#content .js-btn-publish-chapter', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            if (this.classList.contains('loading')) {
                return;
            }
            var link = this;
            var url = link.href;
            post(url, undefined, [['X-AJAX', '1']])
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setChapterPublished(link, response.published);
                }).then(null, core.handleError).then(function() {
                    this.classList.remove('loading');
                }.bind(this));
            this.classList.add('loading');
        });

        // Одобрение
        core.bind('#content .js-story-approve-btn', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            if (this.classList.contains('loading')) {
                return;
            }
            var url = this.href;
            post(url, undefined, [['X-AJAX', '1']])
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setApproved(response.story_id, response.approved);
                }).then(null, core.handleError).then(function() {
                    this.classList.remove('loading');
                }.bind(this));
            this.classList.add('loading');
        });

        // Закрепление на главной
        core.bind('#content .js-story-pin-btn', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            post(url, undefined, [['X-AJAX', '1']])
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                }).catch(core.handleError);
        });

        // Добавление в избранное
        core.bind('.story_favorite', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            post(url, undefined, [['X-AJAX', '1']])
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setFavorited(response.story_id, response.favorited, response.change_url);
                }).catch(core.handleError);
        });

        // Добавление в закладки
        core.bind('.story_bookmark', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            post(url, undefined, [['X-AJAX', '1']])
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setBookmarked(response.story_id, response.bookmarked, response.change_url);
                }).catch(core.handleError);
        });

        // Редактирование доступа
        this.contributorsStuff();

        // Подтверждение удаления рассказа
        var delForm = document.getElementsByClassName('js-story-delete-form')[0];
        if (delForm && delForm.agree) {
            delForm.agree.checked = false;
            delForm.getElementsByClassName('js-story-delete-btn')[0].disabled = true;
            delForm.agree.addEventListener('change', function() {
                delForm.getElementsByClassName('js-story-delete-btn')[0].disabled = !delForm.agree.checked;
            });
        }
    },

    unload: function() {
        if (this.contributorsForm) {
            var selects = this.contributorsForm.getElementsByClassName('js-access-selector');
            for (var i = 0; i < selects.length; i++) {
                selects[i].removeEventListener('change', this._contributorsChangeEventBinded);
            }
            this.contributorsForm.removeEventListener('submit', this._contributorsSendEventBinded);
            this._contributorsChangeEventBinded = null;
            this._contributorsSendEventBinded = null;
            this.contributorsForm = null;
        }
        this.removeChapterPreviewStuff();
        this.removePanel();
    },

    setPublished: function(storyId, published) {
        var story = document.getElementById('story_' + parseInt(storyId));
        if (!story) {
            return false;
        }
        var btn = story.querySelector('.js-story-publish-btn');
        if (btn) {
            let message;
            if (published) {
                btn.classList.remove('entity-publish');
                btn.classList.add('entity-draft');
                message = 'В черновики';
            } else {
                btn.classList.remove('entity-draft');
                btn.classList.add('entity-publish');
                message = 'Опубликовать';
            }
            btn.title = message;
            btn.ariaLabel = message;
            return true;
        } else {
            return false;
        }
    },

    setChapterPublished: function(btn, published) {
        if (btn) {
            if (published) {
                btn.classList.remove('btn-primary');
                btn.textContent = 'в черновики';
            } else {
                btn.classList.add('btn-primary');
                btn.textContent = 'опубликовать';
            }
            return true;
        } else {
            return false;
        }
    },

    setApproved: function(storyId, approved) {
        var story = document.getElementById('story_' + parseInt(storyId));
        if (!story) {
            return false;
        }
        var btn = story.querySelector('.js-story-approve-btn');
        if (btn) {
            let message;
            if (approved) {
                message = 'Отозвать';
                btn.classList.remove('entity-approve');
                btn.classList.add('entity-revoke');
            } else {
                message = 'Одобрить';
                btn.classList.remove('entity-revoke');
                btn.classList.add('entity-approve');
            }
            btn.title = message;
            btn.ariaLabel = message;
            return true;
        } else {
            return false;
        }
    },

    setFavorited: function(storyId, favorited, changeUrl) {
        storyId = parseInt(storyId, 10);
        if (isNaN(storyId)) {
            return false;
        }

        var btns = document.querySelectorAll('.js-story-favorite-' + storyId);
        for (var i = 0; i < btns.length; i++) {
            var btn = btns[i];
            if (favorited) {
                btn.classList.remove('inactive');
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
                btn.classList.add('inactive');
            }
            if (changeUrl) {
                btn.href = changeUrl;
            }
        }

        notify(favorited ? 'Рассказ добавлен в избранное' : 'Рассказ удален из избранного');
        return true;
    },

    setBookmarked: function(storyId, bookmarked, changeUrl) {
        storyId = parseInt(storyId, 10);
        if (isNaN(storyId)) {
            return false;
        }

        var btns = document.querySelectorAll('.js-story-bookmark-' + storyId);
        for (var i = 0; i < btns.length; i++) {
            var btn = btns[i];
            if (bookmarked) {
                btn.classList.remove('inactive');
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
                btn.classList.add('inactive');
            }
            if (changeUrl) {
                btn.href = changeUrl;
            }
        }

        notify(bookmarked ? 'Рассказ добавлен в список' : 'Рассказ удален из списка');
        return true;
    },

    _voteButtonClickEvent: function(event, button) {
        if (!core.extraAjaxAllowed()) {
            return;
        }

        event.stopImmediatePropagation();
        event.preventDefault();

        var form = button.form;

        var body = new FormData(form);
        body.append('vote_ajax', '1');
        if (button.name) {
            body.append(button.name, button.value);
        }
        var url = form.action || '';
        form.classList.add('uploading');

        post(url, body)
            .then(function(response) {
                return response.json();
            })
            .then(function(response) {
                if (core.handleResponse(response, url)) {
                    return;
                }
                story.updateStoryVote(response);
            }).catch(core.handleError)
            .then(function() {
                form.classList.remove('uploading');
            });
    },

    updateStoryVote: function(data) {
        if (!data.success) {
            notifyError(data.error || 'Ошибка');
            return true;
        }

        var i;
        var voteViewAreas = document.getElementsByClassName('js-vote-view-' + data.story_id);
        for (i = 0; i < voteViewAreas.length; i++) {
            voteViewAreas[i].innerHTML = data.vote_view_html;
        }

        var vote1Areas = document.getElementsByClassName('js-vote-area-1-' + data.story_id);
        for (i = 0; i < vote1Areas.length; i++) {
            vote1Areas[i].innerHTML = data.vote_area_1_html;
        }

        var vote2Areas = document.getElementsByClassName('js-vote-area-2-' + data.story_id);
        for (i = 0; i < vote2Areas.length; i++) {
            vote2Areas[i].innerHTML = data.vote_area_2_html;
        }

        notify('Ваш голос учтен!');
        return true;
    },

    contributorsStuff: function() {
        if (!amajaxify.isEnabled()) {
            return;
        }
        this.contributorsForm = document.getElementById('story-edit-contributors-form');
        if (!this.contributorsForm) {
            return;
        }

        this._contributorsSendEventBinded = this._contributorsSendEvent.bind(this);
        this.contributorsForm.addEventListener('submit', this._contributorsSendEventBinded);

        this._contributorsChangeEventBinded = this._contributorsChangeEvent.bind(this);
        var selects = this.contributorsForm.getElementsByClassName('js-access-selector');
        for (var i = 0; i < selects.length; i++) {
            selects[i].addEventListener('change', this._contributorsChangeEventBinded);
            this._updateContributorsSelect(selects[i]);
        }
    },

    _contributorsSendEvent: function(event) {
        event.preventDefault();

        var url = this.contributorsForm.getAttribute('data-ajaxaction') ||  this.contributorsForm.action;
        var formData = new FormData(this.contributorsForm);
        formData.append('act', 'save_access');

        this.contributorsForm.act.disabled = true;
        post(url, formData)
            .then(function(response) {
                return response.json();
            })
            .then(function(response) {
                if (core.handleResponse(response, url)) {
                    this.contributorsForm.act.disabled = false;
                    return;
                }

                var parser = document.createElement('div');
                parser.innerHTML = response.form;
                var newForm = parser.firstElementChild;

                this.contributorsForm.removeEventListener('submit', this._contributorsSendEventBinded);
                this.contributorsForm.parentNode.insertBefore(newForm, this.contributorsForm);
                this.contributorsForm.parentNode.removeChild(this.contributorsForm);
                this.contributorsForm = newForm;
                newForm.addEventListener('submit', this._contributorsSendEventBinded);

                var selects = this.contributorsForm.getElementsByClassName('js-access-selector');
                for (var i = 0; i < selects.length; i++) {
                    selects[i].addEventListener('change', this._contributorsChangeEventBinded);
                    this._updateContributorsSelect(selects[i]);
                }

            }.bind(this)).then(null, function(err) {
                this.contributorsForm.act.disabled = false;
                core.handleError(err);
            }.bind(this));

        return false;
    },

    _contributorsChangeEvent: function(event) {
        this._updateContributorsSelect(event.target);
    },

    _updateContributorsSelect: function(select) {
        var field = select.parentNode.parentNode;
        var visibleCheckbox = field.getElementsByClassName('js-visible-selector')[0];
        if (!visibleCheckbox) {
            return false;
        }
        if (select.value == 'author' || select.value === '') {
            visibleCheckbox.parentNode.style.display = 'none';
        } else {
            visibleCheckbox.parentNode.style.display = '';
        }
        return true;
    },

    panelStuff: function() {
        // Плавающая панелька при чтении рассказа
        var panelElem = document.getElementById('story_panel');
        if (!panelElem) {
            return;
        }

        // Проверяем поддержку position: sticky
        var sticky = false;
        panelElem.style.position = 'sticky';
        if (panelElem.style.position == 'sticky') {
            sticky = true;
        } else {
            panelElem.style.position = '';
            panelElem.classList.remove('story-panel-sticky');
            sticky = false;
        }

        this.panel = {
            dom: panelElem,
            stub: document.createElement('div'),
            sticky: sticky,
            isFixed: false,

            positionY: 0,
            maxPositionY: 0,
            panelWidth: 0,

            event: this._panelEvent.bind(this),
            eventResize: this.recalcPanelGeometry.bind(this),
            eventToTop: function(event) {
                event.preventDefault();
                window.scrollTo(0, 0);
                return false;
            },
        };
        if (panelElem.nextSibling) {
            panelElem.parentNode.insertBefore(this.panel.stub, panelElem.nextSibling);
        } else {
            panelElem.parentNode.appendChild(this.panel.stub);
        }
        window.addEventListener('scroll', this.panel.event);
        window.addEventListener('resize', this.panel.eventResize);

        // Кнопка прокрутки наверх
        var scrollDiv = document.getElementById('toTop');
        scrollDiv.addEventListener('click', this.panel.eventToTop);

        panelElem.classList.remove('no-js');
        this.recalcPanelGeometry();

        // Из-за того, что панель занимает место вверху страницы, прокрутка
        // до элементов по хэшу в адресе приводит к залезанию контента
        // под панель; в обработчике будем это фиксить
        this._hashChangeEventBinded = this._hashChangeEvent.bind(this);
        window.addEventListener('hashchange', this._hashChangeEventBinded);
    },

    removePanel: function() {
        if (!this.panel) {
            return;
        }

        var scrollDiv = document.getElementById('toTop');
        scrollDiv.removeEventListener('click', this.panel.eventToTop);

        window.removeEventListener('hashchange', this._hashChangeEventBinded);
        window.removeEventListener('resize', this.panel.eventResize);
        window.removeEventListener('scroll', this.panel.event);
        this.panel.stub.parentNode.removeChild(this.panel.stub);
        this.panel = null;
    },

    recalcPanelGeometry: function() {
        if (this.panel.sticky) {
            // При position: sticky браузер делает всё сам
            this.panel.event();
            return;
        }

        // Весь код ниже нужен только при отсутствии поддержки sticky
        this.panel.dom.style.position = 'static';
        this.panel.dom.classList.remove('story-panel-floating');
        this.panel.dom.style.width = '';
        this.panel.dom.style.top = '';
        this.panel.stub.style.height = '0px';
        this.panel.isFixed = false;

        var panelRect = this.panel.dom.getBoundingClientRect();
        var contRect = this.panel.dom.parentNode.getBoundingClientRect();

        var scrollTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop;
        var h = panelRect.bottom - panelRect.top;

        this.panel.positionY = scrollTop + panelRect.top;
        this.panel.maxPositionY = scrollTop + contRect.bottom - h;
        this.panel.panelWidth = panelRect.right - panelRect.left;

        this.panel.stub.style.height = h + 'px';

        this.panel.dom.style.position = 'absolute';
        this.panel.dom.style.width = this.panel.panelWidth + 'px';
        this.panel.event();
    },

    _panelEvent: function() {
        var scrollTop = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop;
        var newIsFixed;
        if (this.panel.sticky) {
            newIsFixed = this.panel.dom.getBoundingClientRect().top === 0;
        } else {
            newIsFixed = scrollTop >= this.panel.positionY && scrollTop < this.panel.maxPositionY;
        }
        if (this.panel.isFixed === newIsFixed) {
            return;
        }

        if (newIsFixed) {
            if (!this.panel.sticky) {
                this.panel.dom.style.position = 'fixed';
                this.panel.dom.style.top = '0px';
            }
            this.panel.dom.classList.add('story-panel-floating');
            this.panel.isFixed = true;
        } else {
            if (!this.panel.sticky) {
                this.panel.dom.style.position = 'absolute';
                this.panel.dom.style.top = '';
            }
            this.panel.dom.classList.remove('story-panel-floating');
            this.panel.isFixed = false;
        }
    },

    _hashChangeEvent: function() {
        if (!this.panel || !this.panel.isFixed) {
            return;
        }
        window.scrollBy(0, -this.panel.dom.getBoundingClientRect().height);
    },

    chapterPreviewStuff: function() {
        this._preview.btn = document.getElementById('chapter-preview-btn');
        // this._preview.selectedBtn = document.getElementById('chapter-preview-selected-btn');
        this._preview.area = document.getElementById('chapter-preview');

        // Включаем выбранные пользователем параметры отображения текста главы
        // (кнопочками в story-panel, хотя story-panel на странице
        // редактирования главы нету)
        var chapterText = this._preview.area ? this._preview.area.getElementsByClassName('chapter-text')[0] : null;
        if (chapterText) {
            this.applyFormattingForElement(chapterText);
        }

        if (!window.FormData) {
            this._preview.area = null;
            // this._preview.selectedBtn = null;
            this._preview.btn = null;
            return;
        }

        if (this._preview.btn) {
            this._preview.textInput = this._preview.btn.form.text;
        }

        if (!this._preview.btn || !this._preview.area || !this._preview.textInput) {
            this._preview.btn = null;
            // this._preview.selectedBtn = null;
            this._preview.area = null;
            return;
        }

        this._preview.btnEvent = function(event) {
            this.previewChapter(this._preview.btn.form, false);
            event.preventDefault();
            return false;
        }.bind(this);

        this._preview.btn.addEventListener('click', this._preview.btnEvent);

        // if (this._preview.selectedBtn) {
        //     this._preview.selectedBtnEvent = function(event) {
        //         this.previewChapter(this._preview.selectedBtn.form, true);
        //         event.preventDefault();
        //         return false;
        //     }.bind(this);
        //
        //     this._preview.selectedBtn.addEventListener('click', this._preview.selectedBtnEvent);
        // }

        this._preview.textInputSelectEvent = function(event) {
            var textarea = this._preview.textInput;

            if (textarea.selectionStart || textarea.selectionStart == '0') {
                var startPos = textarea.selectionStart;
                var endPos = textarea.selectionEnd;

                var btn = this._preview.selectedBtn;

                if (startPos !== endPos) {
                    this._preview.selection = [startPos, endPos];
                    if (btn) {
                        btn.disabled = false;
                    }
                } else {
                    this._preview.selection = null;
                    if (btn) {
                        btn.disabled = true;
                    }
                }
            }
        }.bind(this);

        this._preview.textInput.addEventListener('select', this._preview.textInputSelectEvent);
        // emulate "unselect" event (but "blur" event is not required here)
        this._preview.textInput.addEventListener('click', this._preview.textInputSelectEvent);
        this._preview.textInput.addEventListener('focus', this._preview.textInputSelectEvent);
        this._preview.textInput.addEventListener('input', this._preview.textInputSelectEvent);
        this._preview.textInput.addEventListener('change', this._preview.textInputSelectEvent);
    },

    removeChapterPreviewStuff: function() {
        if (this._preview.textInputSelectEvent) {
            this._preview.textInput.removeEventListener('select', this._preview.textInputSelectEvent);
            this._preview.textInput.removeEventListener('click', this._preview.textInputSelectEvent);
            this._preview.textInput.removeEventListener('focus', this._preview.textInputSelectEvent);
            this._preview.textInput.removeEventListener('input', this._preview.textInputSelectEvent);
            this._preview.textInput.removeEventListener('change', this._preview.textInputSelectEvent);
            this._preview.textInputSelectEvent = null;
        }
        if (this._preview.btnEvent) {
            this._preview.btn.removeEventListener('click', this._preview.btnEvent);
            this._preview.btnEvent = null;
        }
        // if (this._preview.selectedBtnEvent) {
        //     this._preview.selectedBtn.removeEventListener('click', this._preview.selectedBtnEvent);
        //     this._preview.selectedBtnEvent = null;
        // }

        var loadingImg = document.getElementById('chapter-preview-loading-img');
        if (loadingImg) {
            loadingImg.style.display = 'none';
        }

        this._preview.selection = null;
        this._preview.textInput = null;
        this._preview.area = null;
        this._preview.btn = null;
        this._preview.selectedBtn = null;
    },

    chapterLinterStuff: function() {
        if (!window.history) {
            return;
        }

        // Проверяем, что это страница редактирования главы
        if (!document.getElementById('chapter-preview')) {
            return;
        }

        // Убираем параметр lint из ссылки, чтобы не мешался
        var url = window.location.toString();
        var urlFixed = url.replace(/\?lint=[A-Za-z0-9_-]+$/, '');
        urlFixed = urlFixed.replace(/\?l=1$/, '');
        if (urlFixed !== url) {
            window.history.replaceState(window.history.state, '', urlFixed);
        }
    },

    previewChapter: function(form, onlySelected) {
        var data = new FormData(form);
        data.append('act', (onlySelected && this._preview.selection) ? 'preview_selected' : 'preview');
        data.append('ajax', '1');
        if (onlySelected && this._preview.selection) {
            data.append('sel_start', this._preview.selection[0].toString());
            data.append('sel_end', this._preview.selection[1].toString());
        }

        var loadingImg = document.getElementById('chapter-preview-loading-img');

        var url = form.action || location.toString();
        post(url, data)
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (loadingImg) {
                    loadingImg.style.display = 'none';
                }
                if (core.handleResponse(data, url)) {
                    return;
                }
                if (this._preview.area) {
                    // Запихиваем HTML-код предпросмотра на страницу
                    this._preview.area.innerHTML = data.html;
                    // И включаем выбранные пользователем параметры отображения
                    // (кнопочками в story-panel, хотя story-panel на странице
                    // редактирования главы нету)
                    var chapterText = this._preview.area.getElementsByClassName('chapter-text')[0];
                    if (chapterText) {
                        this.applyFormattingForElement(chapterText);
                    }
                }
            }.bind(this)).then(null, function(exc) {
                if (loadingImg) {
                    loadingImg.style.display = 'none';
                }
                core.handleError(exc);
            });

        loadingImg.style.display = '';
    },

    // formatting stuff

    initStoryFormatting: function() {
        this._formatting.form = document.getElementsByClassName('js-story-formatting-form')[0];
        if (!this._formatting.form) {
            console.warn('Formatting form not found');
            return;
        }

        this.applyFormattingFromLocalStorage();
        this._formatting.form.addEventListener('change', this._formattingFormChange.bind(this));

        core.utils.addLiveClickListener('js-formatting-btn', this.toggleFormattingFormVisibility.bind(this));
        core.utils.addLiveClickListener('js-formatting-reset-btn', this.resetFormatting.bind(this));
        this._formatting.form.getElementsByClassName('close')[0].addEventListener('click', this.hideFormattingForm.bind(this));
    },

    /**
     * Переключает видимость окна форматирования текста глав.
     */
    toggleFormattingFormVisibility: function() {
        if (!this._formatting.form) {
            return;
        }
        if (this._formatting.visible) {
            this.hideFormattingForm();
        } else {
            this.showFormattingForm();
        }
    },

    /**
     * Отображает окно форматирования текста глав. Попутно активирует
     * все кнопки, включающие отображение, и вешает обработку клика на body,
     * чтобы при клике за пределами окна закрыть его.
     */
    showFormattingForm: function() {
        if (!this._formatting.form || this._formatting.visible) {
            return;
        }
        this._formatting.form.classList.add('hiding');
        this._formatting.form.classList.remove('hidden');
        this._formatting.form.offsetWidth; // force reflow
        this._formatting.form.classList.remove('hiding');
        this._formatting.visible = true;

        var btns = document.getElementsByClassName('js-formatting-btn');
        for (var i = 0; i < btns.length; i++) {
            btns[i].classList.add('active');
        }

        if (!this._formatting.bodyClickEvent) {
            this._formatting.bodyClickEvent = function(event) {
                if (event.target.classList.contains('js-formatting-btn')) {
                    return;
                }
                if (event.target.parentNode && event.target.parentNode.classList.contains('js-formatting-btn')) {
                    return;
                }
                if (!this._formatting.form.contains(event.target)) {
                    this.hideFormattingForm();
                }
            }.bind(this);
            document.body.addEventListener('mousedown', this._formatting.bodyClickEvent);
        }
    },

    /**
     * Скрывает окно форматирования текста глав. Попутно деактивирует
     * все кнопки, включающие отображение, и убирает обработчик body,
     * который был нужен для закрытия окна по клику.
     */
    hideFormattingForm: function() {
        if (!this._formatting.form || !this._formatting.visible) {
            return;
        }
        this._formatting.form.classList.add('hiding');
        this._formatting.visible = false;

        var btns = document.getElementsByClassName('js-formatting-btn');
        for (var i = 0; i < btns.length; i++) {
            btns[i].classList.remove('active');
        }

        setTimeout(function() {
            if (this._formatting.visible) {
                return;
            }
            this._formatting.form.classList.add('hidden');
            this._formatting.form.classList.remove('hiding');
        }.bind(this), 150);

        if (this._formatting.bodyClickEvent) {
            document.body.removeEventListener('mousedown', this._formatting.bodyClickEvent);
            this._formatting.bodyClickEvent = null;
        }
    },

    /**
     * Применяет форматирование к указанному массиву элементов. Если массив
     * не указан, применяет ко всем элементам с классом js-story-formatting.
     * Вызывает applyFormattingForElement для каждого элемента.
     */
    applyFormatting: function(elements) {
        if (elements === undefined || elements === null) {
            elements = Array.prototype.slice.call(document.getElementsByClassName('js-story-formatting'));
        }

        for (var i = 0; i < elements.length; i++) {
            this.applyFormattingForElement(elements[i]);
        }
    },

    /**
     * Применяет форматирование текста к указанном элементу согласно
     * настройкам. Попутно проводит валидацию настроек: некорректные значения
     * сбрасывает на значения по умолчанию (точнее, на null). После применения
     * пытается вернуть прокрутку страницы к тому месту текста, где он был
     * перед форматированием.
     */
    applyFormattingForElement: function(element) {
        var scrollingOrigin = common.getOrigin(element, 50);

        var current = this._formatting.current;

        // font
        if (current.font == 'serif') {
            element.classList.remove('mono-font');
            element.classList.add('serif-font');
        } else if (current.font == 'monospace') {
            element.classList.add('mono-font');
            element.classList.remove('serif-font');
        } else {
            if (current.font != 'sans') {
                current.font = null;
            }
            element.classList.remove('mono-font');
            element.classList.remove('serif-font');
        }

        // align
        if (current.align == 'justify') {
            element.classList.add('mode-justify');
        } else {
            if (current.align != 'left') {
                current.align = null;
            }
            element.classList.remove('mode-justify');
        }

        // size
        if (current.size == 'small') {
            element.classList.remove('big-font');
            element.classList.add('small-font');
        } else if (current.size == 'big') {
            element.classList.add('big-font');
            element.classList.remove('small-font');
        } else {
            if (current.size != 'normal') {
                current.size = null;
            }
            element.classList.remove('big-font');
            element.classList.remove('small-font');
        }

        // hyphens
        if (current.hyphens == 'yes') {
            if (!hypher) {
              // Late initialization to save resources
              hypher = new Hypher(ruHyphenation);
            }
            if (!element.classList.contains('with-hypher')) {
                // TODO: internationalization
                hyphenateDOM(hypher, element);
                element.classList.add('with-hypher');
            }
            element.classList.add('mode-hyphens');
        } else {
            if (current.hyphens != 'no') {
                current.hyphens = null;
            }
            element.classList.remove('mode-hyphens');
        }

        // paragraph
        if (current.paragraph == 'indent') {
            element.classList.remove('mode-indent-both');
            element.classList.add('mode-indent-left');
        } else if (current.paragraph == 'both') {
            element.classList.add('mode-indent-both');
            element.classList.remove('mode-indent-left');
        } else {
            if (current.paragraph != 'space') {
                current.paragraph = null;
            }
            element.classList.remove('mode-indent-both');
            element.classList.remove('mode-indent-left');
        }

        if (scrollingOrigin !== null) {
            common.restoreScrollByOrigin(scrollingOrigin[0], scrollingOrigin[1], scrollingOrigin[2]);
        }
    },

    /**
     * Загружает параметры форматирования из localStorage, обновляет поля
     * в окне форматирования и применяет форматирование ко всем
     * js-story-formatting.
     */
    applyFormattingFromLocalStorage: function() {
        if (!this._formatting.form) {
            return;
        }

        var newStyle;
        try {
            newStyle = JSON.parse(window.localStorage[this._lsFormattingKey] || '{}');
        } catch (e) {
            console.warn('Cannot load formatting from local storage: ' + e);
            return;
        }

        this.loadFormattingFromObject(newStyle);
    },

    /**
     * Загружает и применяет форматирование из указанного словаря.
     * в localStorage не сохраняет, но форму в окне обновляет.
     */
    loadFormattingFromObject: function(newStyle) {
        if (!this._formatting.form) {
            return;
        }

        var form = this._formatting.form;
        var current = this._formatting.current;

        // null означает значение по умолчанию, которое в будущем может меняться,
        // поэтому именно null, а не 'sans'
        current.font = newStyle.font || null;
        form.font.value = current.font || 'sans';

        current.align = newStyle.align || null;
        form.align.value = current.align || 'left';

        current.size = newStyle.size || null;
        form.size.value = current.size || 'normal';

        current.hyphens = newStyle.hyphens || null;
        form.hyphens.value = current.hyphens || 'no';

        current.paragraph = newStyle.paragraph || null;
        form.paragraph.value = current.paragraph || 'space';

        this.applyFormatting();
    },

    /**
     * Обновляет указанный параметр форматированияи, применяет форматирование
     * ко всем js-story-formatting и сохраняет это всё дело в localStorage.
     */
    setFormattingProperty: function(name, value) {
        if (this._formatting.current.hasOwnProperty(name) && this._formatting.current[name] != value) {
            this._formatting.current[name] = value;
            this.applyFormatting();
            if (window.localStorage) {
                window.localStorage[this._lsFormattingKey] = JSON.stringify(this._formatting.current);
            }
        }
    },

    /**
     * Сбрасывает форматирование на значения по умолчанию, применяет
     * и сохраняет это.
     */
    resetFormatting: function() {
        if (!this._formatting.form) {
            return;
        }

        this.loadFormattingFromObject({
            font: null,
            align: null,
            size: null,
            hyphens: null,
            paragraph: null
        });
        if (window.localStorage) {
            window.localStorage[this._lsFormattingKey] = JSON.stringify(this._formatting.current);
        }
    },

    _formattingFormChange: function(event) {
        this.setFormattingProperty(event.target.name, event.target.value);
    }
};

export default story;
