# -*- coding: utf-8 -*-


def init_bl():
    from mini_fiction.bl import registry, authors, stories, comments, htmlblocks, staticpages, news
    from mini_fiction.bl import sorting, logopics, adminlog

    registry.register('bl.author', authors.AuthorBL)
    registry.register('bl.story', stories.StoryBL)
    registry.register('bl.story_local_thread', stories.StoryLocalThreadBL)
    registry.register('bl.chapter', stories.ChapterBL)
    registry.register('bl.story_comment', comments.StoryCommentBL)
    registry.register('bl.story_local_comment', comments.StoryLocalCommentBL)
    registry.register('bl.htmlblock', htmlblocks.HtmlBlockBL)
    registry.register('bl.staticpage', staticpages.StaticPageBL)
    registry.register('bl.newsitem', news.NewsItemBL)
    registry.register('bl.news_comment', comments.NewsCommentBL)
    registry.register('bl.category', sorting.CategoryBL)
    registry.register('bl.character', sorting.CharacterBL)
    registry.register('bl.charactergroup', sorting.CharacterGroupBL)
    registry.register('bl.classifier', sorting.ClassifierBL)
    registry.register('bl.logopic', logopics.LogopicBL)
    registry.register('bl.adminlog', adminlog.AdminLogBL)
