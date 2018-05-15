#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mini_fiction.utils.misc import Paginator


class Commentable(object):
    def has_comments_access(self, author=None):
        # it should be redirected to FooComment.bl.has_comments_access
        raise NotImplementedError

    def access_for_commenting_by(self, author=None):
        # it should be redirected to FooComment.bl.access_for_commenting_by
        raise NotImplementedError

    def create_comment(self, author, ip, data):
        # it should be redirected to FooComment.bl.create
        raise NotImplementedError

    def select_comments(self):
        # should be like `orm.select(c for c in FooComment if c.objattr == self.model)`
        # (`c` variable is required for order_by, don't use something other)
        raise NotImplementedError

    def select_comment_ids(self):
        # should be like `orm.select(c.id for c in FooComment if c.objattr == self.model)`
        # (`c` variable is required for order_by, don't use something other)
        raise NotImplementedError

    def comment2html(self, text):
        # it should be redirected to FooComment.bl.text2html
        raise NotImplementedError

    def select_comment_votes(self, author, comment_ids):
        # should return {comment_id: vote_value}
        return {}

    def get_comments_list(self, maxdepth=None, root_offset=None, root_count=None, root_id=None):
        result = self.select_comments()

        if maxdepth is not None:
            result = result.filter(lambda x: x.tree_depth <= maxdepth)

        if root_offset is not None and root_count is not None:
            if root_id is not None:
                raise ValueError('Cannot combine root_offset/root_count with root_id')
            if root_offset < 0:
                root_offset = 0
            if root_count < 1:
                return []

            # FIXME: filter не дружит с select_comment_ids, но оптимизировать нужно
            comment_ids = self.select_comments().filter(lambda x: x.tree_depth == 0).order_by('c.id')[:]
            comment_ids = [c.id for c in comment_ids]
            if not comment_ids or len(comment_ids) <= root_offset:
                return []

            offset_to = root_offset + root_count - 1
            if offset_to >= len(comment_ids):
                offset_to = len(comment_ids) - 1

            result = result.filter(
                lambda x: x.root_id >= comment_ids[root_offset] and x.root_id <= comment_ids[offset_to]
            )

        elif root_id is not None:
            result = result.filter(lambda x: x.root_id == root_id)

        result = result.order_by('c.id')
        return result[:]

    def get_comments_tree(self, maxdepth=None, root_offset=None, root_count=None, root_id=None, last_viewed_comment=None):
        # Примечание: избегайте использования c.root_id и c.tree_depth в этом методе
        # при вызове его с параметрами по умолчанию, так как он используется
        # в команде checkcomments, что подразумевает, что root_id и tree_depth
        # могут врать
        tree = []
        comments_dict = {}
        comments = self.get_comments_list(None, root_offset, root_count, root_id)  # maxdepth=None для подсчёта числа вложенных комментов

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

    def get_comments_tree_list(self, maxdepth=None, root_offset=None, root_count=None, root_id=None, last_viewed_comment=None):
        return self._comments_tree_iter(self.get_comments_tree(maxdepth, root_offset, root_count, root_id, last_viewed_comment=last_viewed_comment))

    def paginate_comments(self, comments_page=1, per_page=25, maxdepth=None, last_viewed_comment=None):
        target = self.model  # pylint: disable=e1101

        comments_count = target.comments.select().count()
        if comments_count > 0:
            root_comments_total = self.select_comments().filter(lambda x: x.tree_depth == 0).count()
        else:
            root_comments_total = comments_count

        paged = Paginator(
            number=comments_page,
            total=root_comments_total,
            per_page=per_page,
        )  # TODO: restore orphans?

        # paginate_comments вызывается откуда попало, и endpoint запроса
        # неприменим или вообще не существует
        paged.endpoint = None
        paged.view_args = None

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
