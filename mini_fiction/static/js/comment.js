'use strict';

core.define('comment', {
    addlink: null,
    form: null,

    load: function() {
        this.addlink = document.getElementById('comment-add-link');
        this.form = document.getElementById('comment-form');
        if (this.addlink && this.form) {
            core.bind('#content .comment-answer-link', 'click', this._answerEvent);
            this.addlink.addEventListener('click', this._answerEvent);
            this.form.addEventListener('submit', this.submitForm.bind(this));
        }

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

    unload: function() {
        this.addlink = null;
        this.form = null;
    },

    loadModal: function(modalElement) {
        var deleteBtn = modalElement.querySelector('.ajax_comment_delete');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', this._deleteOrRestoreEvent);
        }
        var restoreBtn = modalElement.querySelector('.ajax_comment_restore');
        if (restoreBtn) {
            restoreBtn.addEventListener('click', this._deleteOrRestoreEvent);
        }
    },

    setCommentForm: function(commentId) {
        var after = this.addlink;
        if (commentId === null || commentId === undefined || isNaN(commentId)) {

            this.form.parent.value = 0;
            this.form.style.marginLeft = '0';
        } else {
            var comment = document.getElementById(commentId.toString());
            if (comment) {
                after = comment;
                this.form.parent.value = commentId;
                this.form.style.marginLeft = parseInt(comment.dataset.depth) + 1 + '%';
            } else {
                this.form.parent.value = 0;
                this.form.style.marginLeft = '0';
            }
        }

        if (after) {
            after.parentNode.insertBefore(this.form, after.nextElementSibling);
        } else {
            this.addlink.parentNode.appendChild(this.form);
        }
    },

    submitForm: function(event) {
        if (event) {
            event.preventDefault();
        }

        var form = this.form;
        core.ajax.post(form.action, new FormData(form))
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (core.handleResponse(data, form.action)) {
                    return;
                }
                form.text.value = '';
                if (data.link) {
                    core.goto('GET', data.link);
                }
            })
            .catch(core.handleError)
            .then(function() {
                form.text.disabled = false;
                form.querySelector('input[type="submit"]').disabled = false;
            });
        form.text.disabled = true;
        form.querySelector('input[type="submit"]').disabled = true;
        return false;
    },

    _answerEvent: function(event) {
        event.preventDefault();
        core.comment.setCommentForm(parseInt(this.dataset.parent || 0));
        return false;
    },

    _deleteOrRestoreEvent: function(event) {
        var form = this.form; // this is button
        core.ajax.post(form.action, new FormData(form))
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (core.handleResponse(data, form.action)) {
                    return;
                }
                var comment = document.getElementById(data.comment.toString());
                if (comment) {
                    comment.innerHTML = data.html;
                }
                history.back();
            })
            .catch(core.handleError);
        event.preventDefault();
        return false;
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
