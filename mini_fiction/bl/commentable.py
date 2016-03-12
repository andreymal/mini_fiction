#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class Commentable(object):
    def can_comment_by(self, author=None):
        raise NotImplementedError

    def get_comments_list(self, maxdepth=None, root_offset=None, root_count=None):
        raise NotImplementedError

    def get_comments_tree(self, maxdepth=None, root_offset=None, root_count=None):
        tree = []
        comments_dict = {}
        comments = self.get_comments_list(maxdepth, root_offset, root_count)

        for c in comments:
            item = [c, []]
            comments_dict[c.id] = item
            if c.parent is None or c.parent.id not in comments_dict:
                tree.append(item)
            else:
                comments_dict[c.parent.id][1].append(item)

        return tree

    def get_comments_tree_list(self, maxdepth=None, root_offset=None, root_count=None):
        return self._comments_tree_iter(self.get_comments_tree(maxdepth, root_offset, root_count))

    def _comments_tree_iter(self, tree):
        result = []
        for x in tree:
            result.append((x[0], len(x[1]) > 0))
            if x[1]:
                result.extend(self._comments_tree_iter(x[1]))
        return result
