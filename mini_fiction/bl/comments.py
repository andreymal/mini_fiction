#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ipaddress

from flask import current_app

from mini_fiction.bl.utils import BaseBL
from mini_fiction.utils.misc import call_after_request as later


class CommentBL(BaseBL):
    def create(self, story, text, user, ip):
        comment = self.model(
            story=story,
            author=user,
            ip=ipaddress.ip_address(ip).exploded,
            text=text,
        )
        comment.flush()

        later(current_app.tasks['sphinx_update_comments_count'].delay, story.id)
        return comment

    def update(self, text):
        self.model.text = text

    def delete(self):
        comment = self.model
        story = comment.story
        comment.delete()
        later(current_app.tasks['sphinx_update_comments_count'].delay, story.id)
