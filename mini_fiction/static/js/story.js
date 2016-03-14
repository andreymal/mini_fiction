'use strict';

core.define('story', {
    panel: null,

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
                    if (core.handleResponsePage(response, url)) {
                        return;
                    }
                    if (response.success) {
                        core.story.setPublished(response.story_id, response.published);
                    } else {
                        core.modal(response.modal);
                    }
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
                    core.story.setApproved(response.story_id, response.approved);
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
                    core.story.setFavorited(response.story_id, response.favorited);
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
                    core.story.setBookmarked(response.story_id, response.bookmarked);
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
                    if (core.handleResponsePage(response, url)) {
                        return;
                    }
                    core.story.updateStoryVote(response);
                }).catch(core.handleError);
        });

        // Сортировка глав рассказа
        $('#sortable_chapters').sortable({
            update: this._sortEvent.bind(this)
        });
    },

    unload: function() {
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

        core.notify(bookmarked ? 'Рассказ добавлен в закладки' : 'Рассказ удален из закладок');
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

    panelStuff: function() {
        // Плавающая панелька при чтении рассказа
        var panel = $("#story_panel");
        if (panel.length != 1) {
            return;
        }
        panel = panel;
        var comments = $('#comments');
        this.panel = {
            positionY: panel.position().top,
            maxPositionY: comments.length ? (comments.position().top - panel.outerHeight()) : null,
            panelWidth: panel.width(),
            isFixed: false,
            event: function() {
                this._panelEvent.call(window, this.panel);
            }.bind(this)
        };
        window.addEventListener('scroll', this.panel.event);
        this.panel.event(); // init

        // Кнопка прокрутки наверх
        var scrollDiv = $('#toTop');
        scrollDiv.hide().removeAttr("href");
        if (this.panel.isFixed){
            scrollDiv.fadeIn("fast");
        }

        this.panel.eventToTop = function() {
            if (!this.panel.isFixed) {
                scrollDiv.fadeOut('fast');
            } else {
                scrollDiv.fadeIn('fast');
            }
        }.bind(this);

        window.addEventListener('scroll', this.panel.eventToTop);
        scrollDiv.click(function() {
            $("html, body").animate({scrollTop: 0}, "slow");
        });

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
    },

    removePanel: function() {
        if (!this.panel) {
            return;
        }
        window.removeEventListener('scroll', this.panel.eventToTop);
        window.removeEventListener('scroll', this.panel.event);
        this.panel = null;
    },

    _panelEvent: function(panel) {
        if (
            this.pageYOffset > (panel.positionY) &&
            (!panel.maxPositionY || this.pageYOffset < panel.maxPositionY)
        ) {
            if (!panel.isFixed) {
                panel.isFixed = true;
                $("#story_panel").css('position', 'fixed').css('top', 0).css('z-index', 10).css('width', panel.panelWidth).css('border-top-right-radius', 0).css('border-top-left-radius', 0);
                $("#wrapper").css('height', $("#story_panel").outerHeight() + 10); // margin-bottom: 10px
            }
        } else if (panel.isFixed) {
            panel.isFixed = false;
            $("#story_panel").css('position', 'static').css('top', 0).css('z-index', 10).css('width', panel.panelWidth).css('border-top-right-radius', 10).css('border-top-left-radius', 10);
            $("#wrapper").css('height', 0);
        }
    },

    _sortEvent: function() {
        var items = $('#sortable_chapters').sortable('toArray', {attribute: 'data-chapter'});
        var data = {chapters: []};
        for (var i = 0; i < items.length; i++) {
            data.chapters.push(parseInt(items[i]));
        }

        var url = '/story/' + document.getElementById('sortable_chapters').dataset.story + '/sort/';
        core.ajax.postJSON(url, data)
            .then(function(response) {
                return response.json();
            })
            .then(function(response) {
                core.handleResponse(response, url);
            }).catch(core.handleError);
    }
});
