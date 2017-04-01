#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ipaddress
from datetime import datetime, timedelta

from pony import orm
from flask import current_app, url_for
from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.comments import STORY_COMMENT, NOTICE_COMMENT


class BaseCommentBL(BaseBL):
    target_attr = None
    can_update = False
    can_vote = False
    schema = None

    def get_permalink(self):
        raise NotImplementedError

    def get_tree_link(self):
        raise NotImplementedError

    def get_answer_link(self):
        raise NotImplementedError

    def get_update_link(self):
        raise NotImplementedError

    def get_delete_link(self):
        raise NotImplementedError

    def get_restore_link(self):
        raise NotImplementedError

    def get_vote_link(self):
        raise NotImplementedError

    def has_comments_access(self, target, author=None):
        return True

    def can_comment_by(self, target, author=None):
        return self.has_comments_access(target, author)

    def can_answer_by(self, author=None):
        c = self.model
        target = getattr(c, self.target_attr)
        return not c.deleted and type(c).bl.can_comment_by(target, author)

    def can_delete_or_restore_by(self, author=None):
        return author and author.is_staff

    def can_vote_by(self, author=None, _value_cache=None):
        if not self.can_vote or not author or not author.is_authenticated:
            return False
        c = self.model
        if not self.has_comments_access(getattr(c, self.target_attr), author):
            return False
        if c.deleted or c.author and c.author.id == author.id:
            return False
        return (_value_cache == 0) if _value_cache is not None else (self.get_user_vote(author) == 0)

    def get_user_vote(self, author=None):
        if not self.can_vote or not author or not author.is_authenticated:
            return 0
        vote = self.model.votes.select(lambda x: x.author.id == author.id).first()
        return vote.vote_value if vote else 0

    def create(self, target, author, ip, data):
        if self.schema is None:
            raise NotImplementedError
        if not self.can_comment_by(target, author):
            raise ValueError('Permission denied')  # TODO: refactor exceptions

        if self.schema:
            data = Validator(self.schema).validated(data)

        if data.get('parent'):
            parent = target.comments.select(lambda x: x.local_id == data['parent'] and not x.deleted).first()
            if not parent:
                raise ValidationError({'parent': [lazy_gettext('Parent comment not found')]})
            if not parent.bl.can_answer_by(author):
                raise ValueError('Permission denied')
        else:
            parent = None

        data = {
            self.target_attr: target,
            'author': author if author and author.is_authenticated else None,
            'author_username': author.username if author and author.is_authenticated else '',
            'ip': ipaddress.ip_address(ip).exploded,
            'parent': parent,
            'tree_depth': parent.tree_depth + 1 if parent else 0,
            'text': data['text'],
        }
        if parent:
            data['root_order'] = parent.root_order
        else:
            last_root_comment = target.comments.select(lambda x: x.tree_depth == 0)
            last_root_comment = last_root_comment.order_by(self.model.root_order.desc()).first()
            data['root_order'] = (last_root_comment.root_order + 1) if last_root_comment else 0

        last_comment = target.comments.select().order_by(self.model.id.desc()).first()
        data['local_id'] = (last_comment.local_id + 1) if last_comment else 1

        data.update(self._attributes_for(data))

        comment = self.model(**data)
        comment.flush()
        if hasattr(target, 'comments_count'):
            target.comments_count += 1
        if parent:
            parent.answers_count += 1
        return comment

    def _attributes_for(self, data):
        return {}

    def update(self, author, ip, data):
        if not self.can_update:
            raise ValueError('Not available')

        if self.schema is None or not hasattr(self.model, 'edits'):
            raise NotImplementedError
        if not self.can_update_by(author):
            raise ValueError('Permission denied')  # TODO: refactor exceptions

        if self.schema:
            data = Validator(self.schema).validated(data)

        comment = self.model
        old_text = comment.text
        new_text = data['text']
        comment.text = new_text
        comment.edits_count += 1
        comment.last_edited_at = datetime.utcnow()
        comment.flush()

        editlog = comment.edits.create(
            editor=author,
            date=comment.last_edited_at,
            old_text=old_text,
            new_text=new_text,
            ip=ipaddress.ip_address(ip).exploded,
        )
        editlog.flush()
        return editlog

    def can_update_by(self, author=None):
        c = self.model
        if c.deleted or not self.can_update or not author or not author.is_authenticated:
            return False
        if author.is_staff:
            return True
        if not self.can_comment_by(getattr(c, self.target_attr), author):
            return False
        if c.author is None or c.author.id != author.id:
            return False
        if c.answers_count > 0:
            return False
        return c.date + timedelta(minutes=current_app.config['COMMENT_EDIT_TIME']) > datetime.utcnow()

    def delete(self, author):
        if not self.can_delete_or_restore_by(author):
            raise ValueError('Permission denied')
        self.model.deleted = True
        self.model.last_deleted_at = datetime.utcnow()

    def restore(self, author):
        if not self.can_delete_or_restore_by(author):
            raise ValueError('Permission denied')
        self.model.deleted = False

    def vote(self, author, value):
        if not author or not author.is_authenticated:
            raise ValidationError({'author': [lazy_gettext("Please log in to vote")]})

        if self.can_vote:
            if not hasattr(self.model, 'votes'):
                raise NotImplementedError
            vote = self.model.votes.select(lambda x: x.author.id == author.id).first()
            if vote is not None:
                raise ValidationError({'author': [lazy_gettext("You already voted")]})

        if not self.can_vote or not self.can_vote_by(author):
            raise ValidationError({'author': [lazy_gettext("You can't vote")]})

        if value not in (-1, 1):
            raise ValidationError({'value': [lazy_gettext('Invalid value')]})

        vote = self.model.votes.create(author=author, vote_value=value)
        vote.flush()
        self.model.vote_total += value
        self.model.vote_count += 1
        return vote


class StoryCommentBL(BaseCommentBL):
    target_attr = 'story'
    can_update = True
    can_vote = True
    schema = STORY_COMMENT

    def has_comments_access(self, target, author=None):
        return target.bl.has_access(author)

    def can_comment_by(self, target, author=None):
        if (not author or not author.is_authenticated) and not current_app.config['STORY_COMMENTS_BY_GUEST']:
            return False
        return target.bl.has_access(author)

    def get_permalink(self):
        c = self.model
        # root_order starts from 0
        page = c.root_order // current_app.config['COMMENTS_COUNT']['page'] + 1
        return url_for('story.view', pk=c.story.id, comments_page=page) + '#' + str(c.local_id)

    def get_tree_link(self):
        return url_for('story_comment.ajax_tree', story_id=self.model.story.id, local_id=self.model.local_id)

    def get_answer_link(self):
        return url_for('story_comment.add', story_id=self.model.story.id, parent=self.model.local_id)

    def get_update_link(self):
        return url_for('story_comment.edit', story_id=self.model.story.id, local_id=self.model.local_id)

    def get_delete_link(self):
        return url_for('story_comment.delete', story_id=self.model.story.id, local_id=self.model.local_id)

    def get_restore_link(self):
        return url_for('story_comment.restore', story_id=self.model.story.id, local_id=self.model.local_id)

    def get_vote_link(self):
        return url_for('story_comment.vote', story_id=self.model.story.id, local_id=self.model.local_id)

    def _attributes_for(self, data):
        return {'story_published': data['story'].published}

    def create(self, *args, **kwargs):
        comment = super().create(*args, **kwargs)
        later(current_app.tasks['sphinx_update_comments_count'].delay, comment.story.id)
        return comment

    def select_by_story_author(self, user):
        from mini_fiction.models import CoAuthorsStory

        return self.model.select(
            lambda x: not x.deleted and x.story in orm.select(y.story for y in CoAuthorsStory if y.author.id == user.id)
        )


class NoticeCommentBL(BaseCommentBL):
    target_attr = 'notice'
    can_update = True
    can_vote = True
    schema = NOTICE_COMMENT

    def can_comment_by(self, target, author=None):
        if (not author or not author.is_authenticated) and not current_app.config['NOTICE_COMMENTS_BY_GUEST']:
            return False
        return True

    def get_permalink(self):
        c = self.model
        # root_order starts from 0
        page = c.root_order // current_app.config['COMMENTS_COUNT']['page'] + 1
        return url_for('notices.show', name=c.notice.name, comments_page=page) + '#' + str(c.local_id)

    def get_tree_link(self):
        return url_for('notice_comment.ajax_tree', notice_id=self.model.notice.id, local_id=self.model.local_id)

    def get_answer_link(self):
        return url_for('notice_comment.add', notice_id=self.model.notice.id, parent=self.model.local_id)

    def get_update_link(self):
        return url_for('notice_comment.edit', notice_id=self.model.notice.id, local_id=self.model.local_id)

    def get_delete_link(self):
        return url_for('notice_comment.delete', notice_id=self.model.notice.id, local_id=self.model.local_id)

    def get_restore_link(self):
        return url_for('notice_comment.restore', notice_id=self.model.notice.id, local_id=self.model.local_id)

    def get_vote_link(self):
        return url_for('notice_comment.vote', notice_id=self.model.notice.id, local_id=self.model.local_id)
