'use strict';

/* global amajaxify: false, core: false, captcha: false, common: false */


var comments = {
    addlink: null,
    form: null,

    _captchaField: null,
    _captchaWrap: null,

    _previewBtn: null,
    _previewArea: null,
    __previewBtnEvent: null,

    load: function() {
        this.addlink = document.getElementById('comment-add-link');
        this.form = document.getElementById('comment-form');
        if (this.addlink && this.form) {
            this.addlink.addEventListener('click', this._answerEvent);
            this.form.addEventListener('submit', this.submitForm.bind(this));
            this.loadCommentsContent();

            this._captchaField = this.form.getElementsByClassName('js-captcha-field')[0];
            this._captchaWrap = this.form.getElementsByClassName('js-captcha-wrap')[0];
        }

        var list = document.getElementById('comments-list');
        if (list) {
            this.bindLinksFor(list);
        }

        this.loadPagination();
        this.commentPreviewStuff();
    },

    loadCommentsContent: function() {
        var tree = document.getElementById('comments-tree');
        if (tree) {
            this.bindTreeLinksFor(tree);
            this.bindLinksFor(tree);
            this.treeAutoload();
        }
    },

    treeAutoload: function() {
        var linkBlock = document.querySelector('#content .comment-tree-ajax-autoload');
        if (!linkBlock) {
            return;
        }
        this.loadTreeFor(null, function() {
            if (location.hash.length > 1 && !isNaN(location.hash.substring(1))) {
                var comment = document.getElementById(location.hash.substring(1));
                if (comment) {
                    comment.scrollIntoView();
                }
            }
            comments.treeAutoload();
        }, linkBlock);
    },

    bindTreeLinksFor: function(element) {
        var links, i;
        links = Array.prototype.slice.call(element.querySelectorAll('.comment-answer-link'));
        for (i = 0; i < links.length; i++) {
            links[i].addEventListener('click', this._answerEvent);
        }

        links = Array.prototype.slice.call(element.querySelectorAll('.comment-tree-loader-link'));
        for (i = 0; i < links.length; i++) {
            links[i].addEventListener('click', this._treeLinkEvent);
        }
    },

    bindLinksFor: function(element) {
        var links, i;
        links = Array.prototype.slice.call(element.querySelectorAll('.vote-up, .vote-down'));
        for (i = 0; i < links.length; i++) {
            links[i].addEventListener('click', this._voteEvent);
        }
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
        this.removeCommentPreviewStuff();
        this._captchaWrap = null;
        this._captchaField = null;
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
                this.form.style.marginLeft = parseInt(comment.getAttribute('data-depth')) + 1 + '%';
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
        var parentComment = null;
        if (form.parent.value && form.parent.value != '0') {
            parentComment = document.getElementById(form.parent.value);
        }

        var formData = new FormData(form);
        formData.append('extra_ajax', '1');
        core.ajax.post(form.action, formData)
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                comments._submittedFormEvent(data, parentComment);
            }).then(null, core.handleError)
            .then(function() {
                form.text.disabled = false;
                form.querySelector('.js-comment-submit-btn').disabled = false;
            });
        form.text.disabled = true;
        form.querySelector('.js-comment-submit-btn').disabled = true;
        if (this._previewArea) {
            this._previewArea.innerHTML = '';
        }
        return false;
    },

    _addComment: function(comment, parentComment) {
        var depth = parseInt(comment.getAttribute('data-depth'), 10);

        if (parentComment) {
            var before = parentComment.nextElementSibling;
            while (before && parseInt(before.getAttribute('data-depth'), 10) >= depth) {
                before = before.nextElementSibling;
            }
            if (before) {
                parentComment.parentNode.insertBefore(comment, before);
            } else {
                parentComment.parentNode.appendChild(comment);
            }
            return true;
        }
        if (document.getElementById('comments-tree')) {
            document.getElementById('comments-tree').appendChild(comment);
            return true;
        }
        return false;
    },

    _submittedFormEvent: function(data, parentComment) {
        var form = this.form;

        common.formSavingGetSavedFields();  // чистит сохранённые формы по команде из кук
        this._updateCaptchaField(data.captcha_html);

        if (core.handleResponse(data, form.action)) {
            return;
        }
        form.text.value = '';
        this.setCommentForm(0);
        if (data.html) {
            var oldCommentDiv = document.getElementById(data.comment.toString());
            if (oldCommentDiv) {
                oldCommentDiv.parentNode.removeChild(oldCommentDiv);
            }

            var d = document.createElement('div');
            d.id = data.comment;
            d.innerHTML = data.html;
            this.bindTreeLinksFor(d.firstElementChild);
            this.bindLinksFor(d.firstElementChild);

            if (!this._addComment(d.firstElementChild, parentComment)) {
                amajaxify.goto('GET', data.link);
            }
        } else if (data.link) {
            amajaxify.goto('GET', data.link);
        }
    },

    _updateCaptchaField: function(captchaHtml) {
        captcha.unload(this._captchaWrap);

        if (!captchaHtml) {
            this._captchaField.style.display = 'none';
            return;
        }

        this._captchaField.style.display = '';
        this._captchaWrap.innerHTML = captchaHtml;
        captcha.load(this._captchaWrap);
    },

    _answerEvent: function(event) {
        event.preventDefault();
        comments.setCommentForm(parseInt(this.getAttribute('data-parent') || 0));
        return false;
    },

    _deleteOrRestoreEvent: function(event) {
        var form = this.form; // this is button
        var formData = new FormData(form);
        formData.append('extra_ajax', '1');
        core.ajax.post(form.action, formData)
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
                    comments.bindTreeLinksFor(comment);
                    comments.bindLinksFor(comment);
                }
                history.back();
            })
            .then(null, core.handleError);
        event.preventDefault();
        return false;
    },

    _commentBtnEvent: function(event) {
        event.stopImmediatePropagation();
        event.preventDefault();

        var url = this.getAttribute('data-ajax-href');
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
                comments._commentProcess(data);
            }).then(null, core.handleError).then(function() {
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
    },

    _treeLinkEvent: function(event) {
        comments.loadTreeFor(this.getAttribute('data-for'));
        event.preventDefault();
        return false;
    },

    loadTreeFor: function(commentId, onend, linkBlock) {
        if (!linkBlock) {
            linkBlock = document.getElementById('comment_tree_' + commentId);
        }
        if (!linkBlock) {
            return false;
        }

        var href = linkBlock.getAttribute('data-ajax-href');
        if (!href) {
            return false;
        }

        linkBlock.classList.add('comment-tree-loading');
        var p = core.ajax.fetch(href)
            .then(function(response) {
                return response.json();
            }).then(function(data) {
                if (core.handleResponse(data, href)) {
                    return;
                }
                comments._treeLoadedEvent(linkBlock, data);
            }).catch(core.handleError).then(function() {
                linkBlock.classList.remove('comment-tree-loading');
            });
        if (onend) {
            p = p.then(onend);
        }

        return true;
    },

    _treeLoadedEvent: function(linkBlock, data) {
        var d = document.createElement('div');
        d.innerHTML = data.comments_tree;
        this.bindTreeLinksFor(d);
        this.bindLinksFor(d);
        while (d.firstChild) {
            linkBlock.parentNode.insertBefore(d.firstChild, linkBlock);
        }
        linkBlock.parentNode.removeChild(linkBlock);
    },

    _voteEvent: function(event) {
        event.preventDefault();
        if (this.classList.contains('vote-disabled')) {
            return false;
        }
        comments.vote(this.parentNode, this.classList.contains('vote-down') ? -1 : 1);
        return false;
    },

    vote: function(voteArea, value) {
        if (!voteArea) {
            return false;
        }

        var formData = new FormData();
        formData.append('value', value);

        var href = voteArea.getAttribute('data-href');
        voteArea.classList.add('voting');
        core.ajax.post(href, formData)
            .then(function(response) {
                return response.json();
            }).then(function(data) {
                if (core.handleResponse(data, href)) {
                    return;
                }
                voteArea.innerHTML = data.html;
                core.notify('Ваш голос учтён');
            }).then(null, core.handleError).then(function() {
                voteArea.classList.remove('voting');
            });
        return true;
    },

    previewComment: function(form) {
        if (!form.text.value) {
            this._previewArea.innerHTML = '';
            return;
        }

        var data = new FormData(form);
        data.append('act', 'preview');
        data.append('ajax', '1');

        var loadingImg = document.getElementById('comment-preview-loading-img');

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
                if (this._previewArea) {
                    this._previewArea.innerHTML = data.html;
                }
            }.bind(this)).then(null, function(exc) {
                if (loadingImg) {
                    loadingImg.style.display = 'none';
                }
                core.handleError(exc);
            });

        loadingImg.style.display = '';
    },

    commentPreviewStuff: function() {
        if (!window.FormData) {
            return;
        }

        this._previewBtn = document.getElementById('comment-preview-btn');
        this._previewArea = document.getElementById('comment-preview');

        if (!this._previewBtn || !this._previewArea) {
            this._previewBtn = null;
            this._previewArea = null;
            return;
        }

        this._previewBtnEvent = function(event) {
            this.previewComment(this._previewBtn.form);
            event.preventDefault();
            return false;
        }.bind(this);

        this._previewBtn.addEventListener('click', this._previewBtnEvent);
    },

    removeCommentPreviewStuff: function() {
        if (this._previewBtnEvent) {
            this._previewBtn.removeEventListener('click', this._previewBtnEvent);
            this._previewBtnEvent = null;
        }
        this._previewBtn = null;
        this._previewArea = null;
    }
};


core.onload(comments.load.bind(comments));
core.onunload(comments.unload.bind(comments));
