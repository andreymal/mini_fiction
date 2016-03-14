'use strict';

core.define('comment', {
    addlink: null,
    form: null,

    load: function() {
        this.addlink = document.getElementById('comment-add-link');
        this.form = document.getElementById('comment-form');
        if (this.addlink && this.form) {
            this.addlink.addEventListener('click', this._answerEvent);
            this.form.addEventListener('submit', this.submitForm.bind(this));
            this.loadCommentsContent();
        }

        this.loadPagination();
    },

    loadCommentsContent: function() {
        core.bind('#content .comment-answer-link', 'click', this._answerEvent);
    },

    loadPagination: function() {
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

        var url = this.dataset.ajaxHref;
        var pagination = document.getElementById('comments-pagination');
        pagination.classList.add('pagination-loading');
        core.ajax.fetch(url)
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (core.handleResponse(data, url)) {
                    return;
                }
                core.comment._commentProcess(data);
            }).catch(core.handleError).then(function() {
                pagination.classList.remove('pagination-loading');
            });
    },

    _commentProcess: function(data) {
        if (data.link) {
            history.replaceState(history.state, '', data.link);
        }
        if (data.pagination) {
            var pagination = document.getElementById('comments-pagination');
            pagination.innerHTML = data.pagination;
            this.loadPagination();
        }
        if (data.comments_tree) {
            var tree = document.getElementById('comments-tree');
            tree.innerHTML = data.comments_tree;
            this.loadCommentsContent();
            tree.scrollIntoView();
        }
        if (data.comments_list) {
            var list = document.getElementById('comments-list');
            list.innerHTML = data.comments_list;
            this.loadCommentsContent();
            list.scrollIntoView();
        }
    }
});
