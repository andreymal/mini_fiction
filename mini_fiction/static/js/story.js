'use strict';

/* global core: false, $: false */


var story = {
    panel: null,
    contributorsForm: null,
    _contributorsSendEventBinded: null,
    _contributorsChangeEventBinded: null,

    _preview: {
        btn: null,
        btnEvent: null,
        selectedBtn: null,
        selectedBtnEvent: null,

        area: null,

        textInput: null,
        textInputSelectEvent: null,
        selection: null,
    },

    init: function() {
        // Каруселька со случайными рассказами
        $("#slides").slidesjs({
            width: 524,
            height: 200,
            navigation: {
                active: true,
                effect: "fade",
            },
            pagination: {
                active: false,
            },
            effect: {
                slide: {
                    speed: 1500,
                },
                fade: {
                    speed: 300,
                    crossfade: false,
                }
            },
            play: {
                active: false,
                effect: "fade",
                interval: 5000,
                auto: true,
                swap: true,
                pauseOnHover: true,
                restartDelay: 2500
            }
        });
        // TODO: расхардкодить
        $('.slidesjs-previous').html('<img src="/static/i/arrow-left.png" />');
        $('.slidesjs-next').html('<img src="/static/i/arrow-right.png" />');
    },

    load: function() {
        this.panelStuff();
        this.chapterPreviewStuff();

        // Обработчики для кнопок работы с рассказом

        // Публикация
        core.bind('#content .story_publish', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            core.ajax.post(url)
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
                }).catch(core.handleError);
        });

        // Публикация главы
        core.bind('#content .js-btn-publish-chapter', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var link = this;
            var url = link.href;
            core.ajax.post(url)
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setChapterPublished(link, response.published);
                }).catch(core.handleError);
        });

        // Одобрение
        core.bind('#content .story_approve', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            core.ajax.post(url)
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setApproved(response.story_id, response.approved);
                }).catch(core.handleError);
        });

        // Закрепление на главной
        core.bind('#content .story_pin', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            core.ajax.post(url)
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
        core.bind('#content .story_favorite', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            core.ajax.post(url)
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setFavorited(response.story_id, response.favorited);
                }).catch(core.handleError);
        });

        // Добавление в закладки
        core.bind('#content .story_bookmark', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            core.ajax.post(url)
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.setBookmarked(response.story_id, response.bookmarked);
                }).catch(core.handleError);
        });

        // Голосование за рассказ
        core.bind('#content .vote-area .star-button', 'click', function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = this.href;
            core.ajax.post(url)
                .then(function(response) {
                    return response.json();
                })
                .then(function(response) {
                    if (core.handleResponse(response, url)) {
                        return;
                    }
                    story.updateStoryVote(response);
                }).catch(core.handleError);
        });

        // Редактирование доступа
        this.contributorsStuff();

        // Сортировка глав рассказа
        $('#sortable_chapters').sortable({
            update: this._sortEvent.bind(this)
        });
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
        var btn = story.querySelector('.story_publish');
        if (btn) {
            if (published) {
                btn.classList.remove('btn-primary');
                btn.textContent = 'В черновики';
            } else {
                btn.classList.add('btn-primary');
                btn.textContent = 'Опубликовать';
            }
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
        var btn = story.querySelector('.story_approve');
        if (btn) {
            if (approved) {
                btn.classList.remove('btn-success');
                btn.textContent = 'Отозвать';
            } else {
                btn.classList.add('btn-success');
                btn.textContent = 'Одобрить';
            }
            return true;
        } else {
            return false;
        }
    },

    setFavorited: function(storyId, favorited) {
        var story = document.getElementById('story_' + parseInt(storyId));
        if (!story) {
            return false;
        }
        var panelOk = false;
        var storyOk = false;
        var panelBtn = document.querySelector('#story_panel .story_favorite');
        if (panelBtn) {
            if (favorited) {
                panelBtn.classList.add('favorited');
            } else {
                panelBtn.classList.remove('favorited');
            }
            panelOk = true;
        }
        var btn = story.querySelector('.story_favorite');
        if (btn) {
            if (favorited) {
                btn.classList.add('favorited');
            } else {
                btn.classList.remove('favorited');
            }
            storyOk = true;
        }

        if (!panelOk && !storyOk) {
            return false;
        }

        core.notify(favorited ? 'Рассказ добавлен в избранное' : 'Рассказ удален из избранного');
        return true;
    },

    setBookmarked: function(storyId, bookmarked) {
        var story = document.getElementById('story_' + parseInt(storyId));
        if (!story) {
            return false;
        }
        var panelOk = false;
        var storyOk = false;
        var panelBtn = document.querySelector('#story_panel .story_bookmark');
        if (panelBtn) {
            if (bookmarked) {
                panelBtn.classList.add('bookmarked');
            } else {
                panelBtn.classList.remove('bookmarked');
            }
            panelOk = true;
        }
        var btn = story.querySelector('.story_bookmark');
        if (btn) {
            if (bookmarked) {
                btn.classList.add('bookmarked');
            } else {
                btn.classList.remove('bookmarked');
            }
            storyOk = true;
        }

        if (!panelOk && !storyOk) {
            return false;
        }

        core.notify(bookmarked ? 'Рассказ добавлен в список' : 'Рассказ удален из списка');
        return true;
    },

    updateStoryVote: function(data) {
        var story = document.getElementById('story_' + parseInt(data.story_id));
        if (!story) {
            return false;
        }
        if (!data.success) {
            core.notifyError(data.error || 'Ошибка');
            return true;
        }
        document.getElementById('stars').innerHTML = data.html;

        var value = parseInt(data.value);
        var stars = document.querySelectorAll('.vote-area .star-button');
        for (var i = 0; i < stars.length; i++){
            var star = stars[i];
            if (i + 1 <= value) {
                star.classList.remove('star-0');
                star.classList.add('star-5');
            } else {
                star.classList.remove('star-5');
                star.classList.add('star-0');
            }
        }

        core.notify('Ваш голос учтен!');
        return true;
    },

    contributorsStuff: function() {
        if (!window.amajaxify.isEnabled()) {
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
        core.ajax.post(url, formData)
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
        this.recalcPanelGeometry();

        // Кнопка прокрутки наверх
        var scrollDiv = document.getElementById('toTop');
        scrollDiv.addEventListener('click', this.panel.eventToTop);

        // Переключение размера и типа шрифта
        var font_selector = $('.select-font');
        var size_selector = $('.select-size');
        var chapter_text = $('.chapter-text');
        font_selector.change(function() {
            if (font_selector.val() == '1')
                chapter_text.removeClass('mono-font serif-font');
            else if (font_selector.val() == '2')
                chapter_text.removeClass('mono-font').addClass('serif-font');
            else if (font_selector.val() == '3')
                chapter_text.removeClass('serif-font').addClass('mono-font');
        });
        size_selector.change(function() {
            if (size_selector.val() == '1')
                chapter_text.removeClass('small-font big-font');
            else if (size_selector.val() == '2')
                chapter_text.removeClass('big-font').addClass('small-font');
            else if (size_selector.val() == '3')
                chapter_text.removeClass('small-font').addClass('big-font');
        });

        panelElem.classList.remove('no-js');
    },

    removePanel: function() {
        if (!this.panel) {
            return;
        }

        var scrollDiv = document.getElementById('toTop');
        scrollDiv.removeEventListener('click', this.panel.eventToTop);

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

    _sortEvent: function() {
        var items = $('#sortable_chapters').sortable('toArray', {attribute: 'data-chapter'});
        var data = {chapters: []};
        for (var i = 0; i < items.length; i++) {
            data.chapters.push(parseInt(items[i]));
        }

        var url = '/story/' + document.getElementById('sortable_chapters').getAttribute('data-story') + '/sort/';
        core.ajax.postJSON(url, data)
            .then(function(response) {
                return response.json();
            })
            .then(function(response) {
                core.handleResponse(response, url);
            }).catch(core.handleError);
    },

    chapterPreviewStuff: function() {
        if (!window.FormData) {
            return;
        }

        this._preview.btn = document.getElementById('chapter-preview-btn');
        this._preview.selectedBtn = document.getElementById('chapter-preview-selected-btn');
        this._preview.area = document.getElementById('chapter-preview');
        if (this._preview.btn) {
            this._preview.textInput = this._preview.btn.form.text;
        }

        if (!this._preview.btn || !this._preview.area || !this._preview.textInput) {
            this._preview.btn = null;
            this._preview.selectedBtn = null;
            this._preview.area = null;
            return;
        }

        this._preview.btnEvent = function(event) {
            this.previewChapter(this._preview.btn.form, false);
            event.preventDefault();
            return false;
        }.bind(this);

        this._preview.btn.addEventListener('click', this._preview.btnEvent);

        if (this._preview.selectedBtn) {
            this._preview.selectedBtnEvent = function(event) {
                this.previewChapter(this._preview.selectedBtn.form, true);
                event.preventDefault();
                return false;
            }.bind(this);

            this._preview.selectedBtn.addEventListener('click', this._preview.selectedBtnEvent);
        }

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
        if (this._preview.selectedBtnEvent) {
            this._preview.selectedBtn.removeEventListener('click', this._preview.selectedBtnEvent);
            this._preview.selectedBtnEvent = null;
        }

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
        core.ajax.post(url, data)
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
                    this._preview.area.innerHTML = data.html;
                }
            }.bind(this)).then(null, function(exc) {
                if (loadingImg) {
                    loadingImg.style.display = 'none';
                }
                core.handleError(exc);
            });

        loadingImg.style.display = '';
    }
};


core.oninit(story.init.bind(story));
core.onload(story.load.bind(story));
core.onunload(story.unload.bind(story));
