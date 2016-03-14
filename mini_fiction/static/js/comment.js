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

        var list = document.getElementById('comments-list');
        if (list) {
            this.bindLinksFor(list);
        }

        this.loadPagination();
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
            core.comment.treeAutoload();
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
        var parentComment = null;
        if (form.parent.value && form.parent.value != '0') {
            parentComment = document.getElementById(form.parent.value);
        }
        core.ajax.post(form.action, new FormData(form))
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                core.comment._submittedFormEvent(data, parentComment);
            }).catch(core.handleError)
            .then(function() {
                form.text.disabled = false;
                form.querySelector('input[type="submit"]').disabled = false;
            });
        form.text.disabled = true;
        form.querySelector('input[type="submit"]').disabled = true;
        return false;
    },

    _submittedFormEvent: function(data, parentComment) {
        var form = this.form;
        if (core.handleResponse(data, form.action)) {
            return;
        }
        form.text.value = '';
        this.setCommentForm(0);
        if (data.html) {
            var d = document.createElement('div');
            d.id = data.comment;
            d.innerHTML = data.html;
            this.bindTreeLinksFor(d.firstElementChild);
            this.bindLinksFor(d.firstElementChild);

            if (parentComment) {
                parentComment.parentNode.insertBefore(d.firstElementChild, parentComment.nextElementSibling);
            } else if (document.getElementById('comments-tree')) {
                document.getElementById('comments-tree').appendChild(d.firstElementChild);
            } else if (data.link) {
                core.goto('GET', data.link);
            }
        } else if (data.link) {
            core.goto('GET', data.link);
        }
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
    },

    _treeLinkEvent: function(event) {
        core.comment.loadTreeFor(this.dataset['for']);
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

        var href = linkBlock.dataset.ajaxHref;
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
                core.comment._treeLoadedEvent(linkBlock, data);
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
        core.comment.vote(this.parentNode, this.classList.contains('vote-down') ? -1 : 1);
        return false;
    },

    vote: function(voteArea, value) {
        if (!voteArea) {
            return false;
        }

        var formData = new FormData();
        formData.append('value', value);

        var href = voteArea.dataset.href;
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
            }).catch(core.handleError).then(function() {
                voteArea.classList.remove('voting');
            });
        return true;
    }
});
