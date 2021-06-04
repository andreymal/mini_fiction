def init_bl():
    from mini_fiction.bl import registry, authors, stories, comments, htmlblocks, staticpages, news
    from mini_fiction.bl import adminlog, tag_categories, tags

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
    registry.register('bl.adminlog', adminlog.AdminLogBL)
    registry.register('bl.tag_category', tag_categories.TagCategoryBL)
    registry.register('bl.tag', tags.TagBL)
