# -*- coding: utf-8 -*-


def init_bl():
    from mini_fiction.bl import registry, authors, stories, comments

    registry.register('bl.author', authors.AuthorBL)
    registry.register('bl.story', stories.StoryBL)
    registry.register('bl.chapter', stories.ChapterBL)
    registry.register('bl.story_comment', comments.StoryCommentBL)
