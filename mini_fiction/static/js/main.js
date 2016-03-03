requestRunning = false;
modalDisplaying = false;

/**
 * ОБРАБОТЧИКИ
 */

var ajax = {

    /**
     * Обработчик ошибок AJAX-подгрузки
     * 
     * @param XMLHttpRequest
     *                object Объект XMLHttpRequest
     * @param ajaxOptions
     *                string Строка, описывающая тип случившейся ошибки
     * @param thrownError
     *                object Объект исключений
     */
    errorhandler : function(XMLHttpRequest, ajaxOptions, thrownError) {
        console.warn(XMLHttpRequest);
        console.warn(ajaxOptions);
        console.warn(thrownError);
    },
    /**
     * Отображение модального окна
     * 
     * @param event
     *                event Событие
     */
    modal : function(event) {
        if (modalDisplaying) {
            return;
        }
        event.stopImmediatePropagation();
        event.preventDefault();
        $('.modal:hidden').remove(); // Fix fox clear DOM
        var url = '/ajax' + $(this).attr('href');
        var modal = $('<div class="modal hide fade"></div>');
        modalDisplaying = true;
        $.ajax({
            dataType : 'html',
            success : function(data) {
                modal.html(data).on('show', function() {
                    var textarea = $('textarea', this);
                    if (textarea.length) {
                        textarea.markItUp(mySettings);
                    }
                }).modal();
            },
            complete : function() {
                modalDisplaying = false;
            },
            type : 'GET',
            url : url
        });
    },
    /**
     * Работа с комментариями
     */
    comment : {
        /**
         * Подгрузка комментариев
         * 
         * @param url
         *                string Адрес страницы подгрузки
         */
        load : function(url) {
            var re_page = new RegExp('/comments/page/([0-9]+)/$');
            var go_page = url.match(re_page)[1] | 0;
            $.ajax({
                type : 'GET',
                dataType : 'html',
                success : function(response) {
                    ajax.comment.process(response, go_page);
                },
                url : url
            });
        },
        /**
         * Обработка подгрузки комментариев
         * 
         * @param comments
         *                string HTML-код переданных комментариев
         * @param page_current
         *                int Текущая страница комментариев
         */
        process : function(comments, page_current) {
            var num_pages = $('#num_pages').val();
            var prev_link = $('#ajax_prev_comment');
            var next_link = $('#ajax_next_comment');
            var re_link = new RegExp('(.+)comments/page/[0-9]+/$');
            var new_href_prev_link = prev_link.attr('href').match(re_link)[1] + 'comments/page/' + (page_current - 1) + '/';
            var new_href_next_link = next_link.attr('href').match(re_link)[1] + 'comments/page/' + (page_current + 1) + '/';
            prev_link.attr('href', new_href_prev_link);
            next_link.attr('href', new_href_next_link);
            $('#comments-list').fadeOut('slow', function(){ $(this).empty().append(comments).fadeIn() });
            $('#ajax_pages_comment').text(page_current + '/' + num_pages);
            if (page_current == 1) {
                prev_link.addClass('hidden');
                next_link.removeClass('hidden');
            } else if (page_current == num_pages) {
                next_link.addClass('hidden');
                prev_link.removeClass('hidden');
            } else {
                next_link.removeClass('hidden');
                prev_link.removeClass('hidden');
            }
        },
        /**
         * Удаление комментария
         * 
         * @param event
         *                event Событие
         */
        remove : function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = '/ajax' + $(this).attr('href');
            $.post(url, function(data) {
                $('#comment_' + data).slideUp('slow').remove();
            }).success(function() {
                $('.modal').modal('hide').remove();
            });
        },
        /**
         * Отправка комментария
         * 
         * @param event
         *                event Событие
         */
        send : function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            if (requestRunning) {
                return;
            }
            $('.comment_submit').attr("disabled", "disabled");
            requestRunning = true;
            form = $('.modal form');
            var url = '/ajax' + form.attr('action');
            $.ajax({
                type : "POST",
                url : url,
                data : form.serialize(),
                success : function(data) {
                    var is_modal = (data.indexOf('modal') > -1);
                    if (is_modal) {
                        $('.modal').html(data);
                        var textarea = $('.modal textarea');
                        if (textarea.length) {
                            textarea.markItUp(mySettings);
                        }
                    } else {
                        var new_comment = $(data);
                        var new_text = $('div.comment', new_comment);
                        var target = $('#' + new_comment.attr('id') + ' div.comment');
                        if (target.length) {
                            target.replaceWith(new_text);
                        } else {
                            $('#comments-list').append(new_comment);
                        }
                        $('.modal').modal('hide').remove();
                    }
                },
                complete : function() {
                    requestRunning = false;
                },
            });
        },

    },
    /**
     * Работа с рассказами
     */
    story : {
        /**
         * Публикация рассказа
         * 
         * @param response
         *                int ID рассказа
         */
        publish : function(response, btn) {
            var re_story_response = new RegExp('^[0-9]{1,10}$');
            if (re_story_response.test(response)) {
                if (btn.hasClass('btn-primary')) {
                    var text = 'В черновики';
                } else {
                    var text = 'Опубликовать';
                }
                btn.text(text).toggleClass('btn-primary');
            } else {
                $('.modal:hidden').remove(); // Fix fox clear DOM
                var modal = $('<div class="modal hide fade"></div>');
                modal.html(response).modal();
            }
        },
        /**
         * Одобрение рассказа
         * 
         * @param response
         *                int ID рассказа
         */
        approve : function(response) {
            if (pages.story_view.regex.test(window.location.pathname) || pages.story_edit.regex.test(window.location.pathname)) {
                var btn = $('.story_approve');
            } else {
                var btn = $('#story_' + response + ' .story_approve');
            }
            if (btn.hasClass('btn-success')) {
                var text = 'Отозвать';
            } else {
                var text = 'Одобрить';
            }
            btn.text(text).toggleClass('btn-success');
        },

        /**
         * Обработать закладку рассказа
         * 
         * @param response
         *                int ID рассказа
         */
        bookmark : function(response) {
            if (pages.story_view.regex.test(window.location.pathname)) {
                var btn = $('.story_bookmark');
                var msg_container = $('.story_bookmark ~ .story_bookmark_msg');
            } else {
                var btn = $('#story_' + response + ' .story_bookmark');
                var msg_container = $('#story_' + response + ' .story_bookmark ~ .story_bookmark_msg');
            }
            if (btn.hasClass('bookmarked')) {
                var text = 'Рассказ удален из закладок';
            } else {
                var text = 'Рассказ добавлен в закладки';
            }
            btn.toggleClass('bookmarked');
            msg_container.append('<span class="alert alert-warning alert-mini">' + text + '</span>');
            msg_container.children().animate({
                opacity : 0.01
            }, 3000, function() {
                msg_container.children().remove();
            });
        },

        /**
         * Обработать избранность рассказа
         * 
         * @param response
         *                int ID рассказа
         */
        favorite : function(response) {
            if (pages.story_view.regex.test(window.location.pathname) || pages.chapter_view.regex.test(window.location.pathname)) {
                var btn = $('.story_favorite');
                var msg_container = $('.story_favorite ~ .story_favorite_msg');
            } else {
                var btn = $('#story_' + response + ' .story_favorite');
                var msg_container = $('#story_' + response + ' .story_favorite ~ .story_favorite_msg');
            }
            if (btn.hasClass('favorited')) {
                var text = 'Рассказ удален из избранного';
            } else {
                var text = 'Рассказ добавлен в избранное';
            }
            btn.toggleClass('favorited');
            msg_container.append('<span class="alert alert-warning alert-mini">' + text + '</span>');
            msg_container.children().animate({
                opacity : 0.01
            }, 3000, function() {
                msg_container.children().remove();
            });
        },
        /**
         * Голосование за рассказ
         * 
         * @param url
         *                string Адрес
         */
        vote : function(url) {
            if (requestRunning) {
                return;
            }
            requestRunning = true;
            $.ajax({
                dataType : 'json',
                success : function(response) {
                    $('#vote-msg').html('<span class="alert alert-success">Ваш голос учтен!</span>');
                    $('#vote-msg span').animate({
                        opacity : 0.1
                    }, 3500, function() {
                        $('#vote-msg span').remove();
                    });

                    $('#stars').html(response['html']);
                    var value = parseInt(response['value']);
                    $('.vote-area .star-button').each(function(i){
                        if(i + 1 <= value){
                            $(this).removeClass('star-0').addClass('star-5');
                        }else{
                            $(this).removeClass('star-5').addClass('star-0');
                        }
                    })
                },
                error : function(response) {
                    try {
                        var data = JSON.parse(response.responseText);
                    }catch(e){
                        var data = {};
                    }
                    $('#vote-msg').html('<span class="alert alert-warning">' + (data.error || 'Ошибка') + '</span>');
                    $('#vote-msg span').animate({
                        opacity : 0.1
                    }, 3500, function() {
                        $('#vote-msg span').remove();
                    });
                },
                complete : function() {
                    requestRunning = false;
                },
                type : 'POST',
                url : url
            });
        },
        /**
         * Удаление рассказа
         * 
         * @param event
         *                event Событие
         */
        remove : function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = '/ajax' + $(this).attr('href');

            $.post(url, function(data) {
                $('#story_' + data).slideUp('slow').remove();
            }).success(function() {
                $('.modal').modal('hide').remove();
                if (pages.story_view.regex.test(window.location.pathname) || pages.story_edit.regex.test(window.location.pathname)) {
                    window.location = '/';
                }
            });
        },
    },
    /**
     * Работа с главами
     */
    chapter : {
        /**
         * Удаление главы по AJAX
         * 
         * @param event
         *                event Событие
         */
        remove : function(event) {
            event.stopImmediatePropagation();
            event.preventDefault();
            var url = '/ajax' + $(this).attr('href');
            $('#sortable_chapters').sortable('destroy');
            $.post(url, function(data) {
                $('#chapter_' + data).slideUp('slow').remove();
            }).success(function() {
                $('.modal').modal('hide').remove();
                listeners.chapter.sortability();
            });
        },
    },
    /**
     * Работа с авторами
     */
    author : {
        /**
         * Одобрение автора
         * 
         * @param response
         *                int ID рассказа
         */
        approve : function(response) {
            var btn = $('#author_approve');
            if (btn.hasClass('btn-primary')) {
                var text = 'Не проверен';
            } else {
                var text = 'Проверен';
            }
            btn.text(text).toggleClass('btn-primary');
        }
    }
}

/**
 * События
 */

var listeners = {
    story : {
        // Удаление
        remove : function() {
            $(document).on('click', '.story_delete', ajax.modal);
            $(document).on('click', '.ajax_story_delete:visible', ajax.story.remove);
        },
        // Одобрение
        approve : function() {
            $('.story_approve').click(function(event) {
                event.stopImmediatePropagation();
                event.preventDefault();
                var url = '/ajax' + $(this).attr('href');
                $.post(url, ajax.story.approve);
            });
        },
        // Публикация

        publish : function() {
            $('.story_publish').click(function(event) {
                event.stopImmediatePropagation();
                event.preventDefault();
                var btn = $(this);
                var url = '/ajax' + btn.attr('href');
                $.post(url, function(response) {
                    ajax.story.publish(response, btn);
                });
            });
        },

        // Закладки
        bookmark : function() {
            $('.story_bookmark').click(function(event) {
                event.stopImmediatePropagation();
                event.preventDefault();
                var url = '/ajax' + $(this).attr('href');
                $.post(url, ajax.story.bookmark);
            });
        },
        // Избранное
        favorite : function() {
            $('.story_favorite').click(function(event) {
                event.stopImmediatePropagation();
                event.preventDefault();
                var url = '/ajax' + $(this).attr('href');
                $.post(url, ajax.story.favorite);
            });
        },
        // Переключение размера и типа шрифта
        style : function() {
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
        // Голосование
        vote : function() {
            var buttons = $('.vote-area .star-button').click(function(event) {
                event.stopImmediatePropagation();
                event.preventDefault();
                var url = '/ajax' + $(this).attr('href');
                ajax.story.vote(url);
                buttons.addClass('unvoted');
                $(this).removeClass('unvoted');
            });
        },
    },
    comment : {
        // Управление AJAX-пагинацией
        pagination : function() {
            $('#ajax_next_comment').click(function(event) {
                event.stopImmediatePropagation();
                event.preventDefault();
                var url = '/ajax' + $(this).attr('href');
                ajax.comment.load(url);
            });
            $('#ajax_prev_comment').click(function(event) {
                event.stopImmediatePropagation();
                event.preventDefault();
                var url = '/ajax' + $(this).attr('href');
                ajax.comment.load(url);
            });
        },
        // Добавление комментария
        add : function() {
            $(document).on('click', '.comment_add', ajax.modal);
        },
        // Редактирование комментария
        edit : function() {
            $(document).on('click', '.comment_edit', ajax.modal);
        },
        // Отправка комментария
        send : function() {
            $(document).on('click', '.modal .comment_submit', ajax.comment.send);
        },
        // Удаление комментария
        remove : function() {
            $(document).on('click', '.comment_delete', ajax.modal);
            $(document).on('click', '.ajax_comment_delete:visible', ajax.comment.remove);
        },
    },
    chapter : {
        remove : function() {
            $(document).on('click', '.chapter_delete', ajax.modal);
            $(document).on('click', '.ajax_chapter_delete:visible', ajax.chapter.remove);
        },
        sortability : function() {
            $('#sortable_chapters').sortable({
                update : function() {
                    $.ajax({
                        data : $('#sortable_chapters').sortable('serialize'),
                        type : 'POST',
                        url : '/ajax/story/' + $('#sortable_chapters').data('story') + '/sort/'
                    });
                }
            });
        },

    },
    author : {
        // Одобрение
        approve : function() {
            $('#author_approve').click(function(event) {
                event.stopImmediatePropagation();
                event.preventDefault();
                var url = '/ajax' + $(this).attr('href');
                $.post(url, ajax.author.approve);
            });
        }
    },
    misc : {
        characters : function() {
            $('.characters-select:checked + img').addClass('ui-selected');
            $(".character-item").click(function() {
        var input = $('input', this);
                var checked = input.prop('checked');
                input.prop('checked', !checked);
                $('img', this).toggleClass('ui-selected', !checked);
            });
        },
        search : function() {
            $("#reset_search").click(function() {
                $('input:checked').prop('checked', false);
                $('button').removeClass('active');
                $('img').removeClass('ui-selected');
                document.getElementById('appendedInputButtons').setAttribute('value', '');
                $('.span8').slideUp();
            });
        }
    }
}

var pages = {
    index : {
        regex : new RegExp('^/$'),
        action : function() {
            $('#nav_index').addClass('active');
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
        }
    },
    story_view : {
        regex : new RegExp('^/story/[0-9]+/(?:comments/page/[0-9]+/)?$'),
        action : function() {
            $('#id_text').markItUp(mySettings)
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
            for ( var listener in listeners.comment) {
                listeners.comment[listener]();
            }
            stuff.panel();
            if ($('#wrapper').hasClass('nsfw')) {
                $('#nsfwModal').modal();
            }
        }
    },
    story_add : {
        regex : new RegExp('^/story/add/$'),
        action : function() {
            $('#nav_story_add').addClass('active');
            $('#id_text').markItUp(mySettings);
            $('#id_notes').markItUp(mySettings);
            listeners.misc.characters();
        }
    },
    story_edit : {
        regex : new RegExp('^/story/[0-9]+/edit/$'),
        action : function() {
            $('#id_text').markItUp(mySettings);
            $('#id_notes').markItUp(mySettings);
            listeners.misc.characters();
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
            for ( var listener in listeners.chapter) {
                listeners.chapter[listener]();
            }
        }
    },
    chapter_view : {
        regex : new RegExp('^/story/[0-9]+/chapter/(?:[0-9]+|all)/$'),
        action : function() {
            stuff.panel();
            if ($('#wrapper').hasClass('nsfw')) {
                $('#nsfwModal').modal();
            }
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
        }
    },
    chapter_add : {
        regex : new RegExp('^/story/[0-9]+/chapter/add/$'),
        action : function() {
            $('#id_text').markItUp(mySettings);
            $('#id_notes').markItUp(mySettings);
        }
    },
    chapter_edit : {
        regex : new RegExp('^/chapter/[0-9]+/edit/$'),
        action : function() {
            $('#id_text').markItUp(mySettings);
            $('#id_notes').markItUp(mySettings);
        }
    },
    comment_add : {
        regex : new RegExp('^/story/[0-9]+/comment/add/$'),
        action : function() {
            $('#id_text').markItUp(mySettings);
        }
    },
    comment_edit : {
        regex : new RegExp('^/story/[0-9]+/comment/[0-9]+/edit/$'),
        action : function() {
            $('#id_text').markItUp(mySettings);
        }
    },
    author_overview : {
        regex : new RegExp('^/accounts/[0-9]+/(?:comments/page/[0-9]+/)?$'),
        action : function() {
            $('#nav_author_overview').addClass('active');
            listeners.author.approve();
            listeners.comment.pagination();
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
        }
    },
    author_dashboard : {
        regex : new RegExp('^/accounts/profile/(?:comments/page/[0-9]+/)?$'),
        action : function() {
            $('#nav_author_dashboard').addClass('active');
            listeners.author.approve();
            listeners.comment.pagination();
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
        }
    },
    registration : {
        regex : new RegExp('^/accounts/register/(.+)?'),
        action : function() {
            $('#nav_registration').addClass('active');
        }
    },
    search : {
        regex : new RegExp('^/search/(.+)?'),
        action : function() {
            $('#nav_search').addClass('active');
            listeners.misc.characters();
            listeners.misc.search();
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
        }
    },
    favorites : {
        regex : new RegExp('^/accounts/[0-9]+/favorites/(.+)?'),
        action : function() {
            $('#nav_favorites').addClass('active');
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
        }
    },
    bookmarks : {
        regex : new RegExp('^/bookmarks/(.+)?'),
        action : function() {
            $('#nav_bookmarks').addClass('active');
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
        }
    },
    submitted : {
        regex : new RegExp('^/submitted/(.+)?'),
        action : function() {
            $('#nav_submitted').addClass('active');
            for ( var listener in listeners.story) {
                listeners.story[listener]();
            }
        }
    },
    help : {
        regex : new RegExp('^/page/help/$'),
        action : function() {
            $('#nav_help').addClass('active');
            $('a.tab_inline[data-toggle="tab"]').click(function() {
                var href = $($(this)['context']).attr('href');
                $('.nav-simple li').removeClass('active');
                $('.nav-simple li a[href="' + href + '"]').parent().addClass('active');

            });
        }
    },
    terms : {
        regex : new RegExp('^/page/terms/$'),
        action : function() {
            $('#nav_terms').addClass('active');
        }
    },
}

var stuff = {
    // Действия на каждом типе страниц
    page : function() {
        for ( var page in pages) {
            if (pages[page].regex.test(window.location.pathname)) {
                pages[page].action()
            }
        }
    },
    // Ротатор шапок
    logo : function() {
        var len = 8
        if ($.cookie('stories_gr') == null) {
            var stories_gr = Math.floor(Math.random() * len) + 1;
            $.cookie('stories_gr', stories_gr, {
                expires : 1
            });
        } else {
            var stories_gr = $.cookie('stories_gr');
        }
        var new_image = "url(/static/i/logopics/logopic-" + stories_gr + ".jpg)";
        $('.logopic').css('background-image', new_image);
    },
    // Плавающая панелька
    panel : function() {
        if(!$("#story_panel").length) return;
        positionY = $("#story_panel").position().top;
        panelWidth = $("#story_panel").width();
        isFixed = false;
        $(window).bind('scroll', function () {
            if (this.pageYOffset > (positionY)) {
                isFixed = true;
                $("#story_panel").css('position', 'fixed').css('top', 0).css('z-index', 10).css('width', panelWidth).css('border-top-right-radius', 0).css('border-top-left-radius', 0);
                $("#wrapper").css('height', $("#story_panel").height() + 30);
            }
            if (this.pageYOffset <= positionY){
                isFixed = false;
                $("#story_panel").css('position', 'static').css('top', 0).css('z-index', 10).css('width', panelWidth).css('border-top-right-radius', 10).css('border-top-left-radius', 10);
                $("#wrapper").css('height', 0);
            }
        });
    },

    // Прокрутка
    scroll : function(){
        $.fn.scrollToTop=function(){
            $(this).hide().removeAttr("href");
            if ($("#story_panel").css('position') == 'fixed' ){
                $(this).fadeIn("slow")
            }
            var scrollDiv=$(this);
            $(window).scroll(function(){
                if($("#story_panel").css('position') == 'static'){
                    $(scrollDiv).fadeOut("slow")
                }else{
                    $(scrollDiv).fadeIn("slow")
                }
            });
            $(this).click(function(){
                $("html, body").animate({scrollTop:0},"slow")
            })
        }
    },

    // Обработка состояний BootStrap Elements
    bootstrap : function() {
        var group = $(this);
        var buttons_container = $('.buttons-visible', group)
        var data_container = $('.buttons-data', group)
        var type = group.hasClass('checkbox') ? 'checkbox' : 'radio'

        // Обработка проставленных заранее чекбоксов и радиоселектов
        $('input', data_container).each(function() {
            var input = $(this);
            var value = input.attr('value');
            if (!!(input.prop('checked'))) {
                $('button[value=' + value + ']', buttons_container).addClass('active');
            }
        });
        // Onclick-обработчик
        $('button', buttons_container).each(
                function() {
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
    // Конфигурация заголовка AJAX-запроса с CSRF Cookie
    ajaxsetup : function() {
        $.ajaxSetup({
            cache : false,
            crossDomain : false,
            error : ajax.errorhandler,
            beforeSend : function(request) {
                var csrftoken = $('meta[name=csrf-token]').attr('content');
                request.setRequestHeader("X-CSRFToken", csrftoken);
            }
        });
    },
    carousel : function() {
        $("#slides").slidesjs({
            width : 524,
            height : 200,
            navigation : {
                active : true,
                effect : "fade",
            },
            pagination : {
                active : false,
            },
            effect : {
                slide : {
                    speed : 1500,
                },
                fade : {
                    speed : 300,
                    crossfade : false,
                }
            },
            play : {
                active : false,
                effect : "fade",
                interval : 5000,
                auto : true,
                swap : true,
                pauseOnHover : true,
                restartDelay : 2500
            }
        });
        $('.slidesjs-previous').html('<img src="/static/i/arrow-left.png" />');
        $('.slidesjs-next').html('<img src="/static/i/arrow-right.png" />');
    }
}
// При загрузке страницы
$(function() {
    stuff.logo();
    stuff.ajaxsetup();
    stuff.carousel();
    $('.bootstrap').each(stuff.bootstrap);
    stuff.page();
    stuff.panel();
});

// Прокрутка
$(function(){
    $.fn.scrollToTop=function(){
        $(this).hide().removeAttr("href");
        if ($("#story_panel").css('position') == 'fixed' ){
            $(this).fadeIn("fast")
        }
        var scrollDiv=$(this);
        $(window).scroll(function(){
            if($("#story_panel").css('position') == 'static'){
                $(scrollDiv).fadeOut("fast")
            }else{
                $(scrollDiv).fadeIn("fast")
            }
        });
        $(this).click(function(){
            $("html, body").animate({scrollTop:0},"slow")
        })
    }
});
$(function() {$("#toTop").scrollToTop();});
