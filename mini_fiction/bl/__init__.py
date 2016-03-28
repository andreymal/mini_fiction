# -*- coding: utf-8 -*-


def init_bl():
    from mini_fiction.bl import registry, authors, stories, comments, htmlblocks, staticpages, notices
    from mini_fiction.bl import sorting

    registry.register('bl.author', authors.AuthorBL)
    registry.register('bl.story', stories.StoryBL)
    registry.register('bl.chapter', stories.ChapterBL)
    registry.register('bl.story_comment', comments.StoryCommentBL)
    registry.register('bl.htmlblock', htmlblocks.HtmlBlockBL)
    registry.register('bl.staticpage', staticpages.StaticPageBL)
    registry.register('bl.notice', notices.NoticeBL)
    registry.register('bl.notice_comment', comments.NoticeCommentBL)
    registry.register('bl.category', sorting.CategoryBL)
    registry.register('bl.character', sorting.CharacterBL)
    registry.register('bl.charactergroup', sorting.CharacterGroupBL)
    registry.register('bl.classifier', sorting.ClassifierBL)
