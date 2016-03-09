'use strict';

core.define('comment', {
    load: function() {
        // Управление AJAX-пагинацией
        var next_btn = document.getElementById('ajax_next_comment');
        if (next_btn) {
            next_btn.addEventListener('click', this._commentBtnEvent);
        }
        var prev_btn = document.getElementById('ajax_prev_comment');
        if (prev_btn) {
            prev_btn.addEventListener('click', this._commentBtnEvent);
        }
    },

    _commentBtnEvent: function(event) {
        event.stopImmediatePropagation();
        event.preventDefault();

        var url = '/ajax' + this.getAttribute('href');
        var re_page = new RegExp('/comments/page/([0-9]+)/$');
        var go_page = url.match(re_page)[1] | 0;
        core.ajax.fetch(url)
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (core.handleResponse(data, url)) {
                    return;
                }
                core.comment._commentProcess(data, go_page);
            }).catch(core.handleError);
    },

    _commentProcess: function(data, page_current) {
        var num_pages = parseInt(document.getElementById('num_pages').value);
        var prev_link = document.getElementById('ajax_prev_comment');
        var next_link = document.getElementById('ajax_next_comment');
        var re_link = new RegExp('(.+)comments/page/[0-9]+/$');
        var new_href_prev_link = prev_link.getAttribute('href').match(re_link)[1] + 'comments/page/' + (page_current - 1) + '/';
        var new_href_next_link = next_link.getAttribute('href').match(re_link)[1] + 'comments/page/' + (page_current + 1) + '/';
        prev_link.setAttribute('href', new_href_prev_link);
        next_link.setAttribute('href', new_href_next_link);

        $('#comments-list').fadeOut('slow', function() {
            $(this).empty().append(data.comments).fadeIn();
        });
        document.getElementById('ajax_pages_comment').textContent = page_current + ' / ' + num_pages;
        if (page_current == 1) {
            prev_link.classList.add('hidden');
            next_link.classList.remove('hidden');
        } else if (page_current == num_pages) {
            next_link.classList.add('hidden');
            prev_link.classList.remove('hidden');
        } else {
            next_link.classList.remove('hidden');
            prev_link.classList.remove('hidden');
        }
    }
});
