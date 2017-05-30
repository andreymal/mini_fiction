#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.utils.misc import Paginator


class Commentable(object):
    def has_comments_access(self, author=None):
        # it should be redirected to FooComment.bl.has_comments_access
        raise NotImplementedError

    def can_comment_by(self, author=None):
        # it should be redirected to FooComment.bl.can_comment_by
        raise NotImplementedError

    def create_comment(self, author, ip, data):
        # it should be redirected to FooComment.bl.create
        raise NotImplementedError

    def select_comments(self):
        # should be like `orm.select(c for c in FooComment if c.objattr == self.model)`
        # (`c` variable is required for order_by, don't use something other)
        raise NotImplementedError

    def select_comment_votes(self, author, comment_ids):
        # should return {comment_id: vote_value}
        return {}

    def get_comments_list(self, maxdepth=None, root_offset=None, root_count=None):
        result = self.select_comments()
        if maxdepth is not None:
            result = result.filter(lambda x: x.tree_depth <= maxdepth)
        if root_offset is not None and root_count is not None:
            offset_to = root_offset + root_count
            result = result.filter(lambda x: x.root_order >= root_offset and x.root_order < offset_to)
        result = result.order_by('c.id')
        return result[:]

    def get_comments_tree(self, maxdepth=None, root_offset=None, root_count=None, last_viewed_comment=None):
        tree = []
        comments_dict = {}
        comments = self.get_comments_list(None, root_offset, root_count)  # maxdepth=None для подсчёта числа вложенных комментов

        for c in comments:
            # Проставляем счётчики вложенных комментов по всей ветке выше
            p = c.parent
            while p:
                if p.id in comments_dict:
                    comments_dict[p.id][2] += 1
                    if last_viewed_comment is not None and last_viewed_comment < c.id:
                        comments_dict[p.id][3] += 1
                p = p.parent
            del p

            # Если столь глубокий коммент у нас не просили, не добавляем его в ветку
            if maxdepth is not None and c.tree_depth > maxdepth:
                continue

            item = [c, [], 0, 0]  # [сам коммент, ответы, число всех вложенных комментов, число вложенных непросмотренных]
            comments_dict[c.id] = item
            if c.parent is None or c.parent.id not in comments_dict:
                tree.append(item)
            else:
                comments_dict[c.parent.id][1].append(item)

        return tree

    def get_comments_tree_list(self, maxdepth=None, root_offset=None, root_count=None, last_viewed_comment=None):
        return self._comments_tree_iter(self.get_comments_tree(maxdepth, root_offset, root_count, last_viewed_comment=last_viewed_comment))

    def paginate_comments(self, comments_page=1, per_page=25, maxdepth=None, last_viewed_comment=None):
        target = self.model  # pylint: disable=e1101

        comments_count = target.comments.select().count()
        if comments_count > 0:
            root_comments_total = self.select_comments().order_by('-c.root_order').first().root_order + 1
        else:
            root_comments_total = comments_count

        paged = Paginator(
            number=comments_page,
            total=root_comments_total,
            per_page=per_page,
        )  # TODO: restore orphans?

        comments_tree_list = target.bl.get_comments_tree_list(
            maxdepth=maxdepth,
            root_offset=per_page * (paged.number - 1),
            root_count=per_page,
            last_viewed_comment=last_viewed_comment,
        )

        return comments_count, paged, comments_tree_list

    def _comments_tree_iter(self, tree):
        result = []
        for x in tree:
            result.append((x[0], len(x[1]) > 0, x[2], x[3]))
            if x[1]:
                result.extend(self._comments_tree_iter(x[1]))
        return result
