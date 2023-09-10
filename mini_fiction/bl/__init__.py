def init_bl():
    from mini_fiction.bl import registry, authors, stories, comments, news
    from mini_fiction.bl import tag_categories

    registry.register('bl.author', authors.AuthorBL)
    registry.register('bl.story', stories.StoryBL)
    registry.register('bl.story_local_thread', stories.StoryLocalThreadBL)
    registry.register('bl.chapter', stories.ChapterBL)
    registry.register('bl.story_comment', comments.StoryCommentBL)
    registry.register('bl.story_local_comment', comments.StoryLocalCommentBL)
    registry.register('bl.newsitem', news.NewsItemBL)
    registry.register('bl.news_comment', comments.NewsCommentBL)
    registry.register('bl.tag_category', tag_categories.TagCategoryBL)
