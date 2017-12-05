#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from flask import url_for, render_template


class BaseDownloadFormat(object):
    extension = None
    name = None
    debug_content_type = 'text/plain'
    chapter_template = None
    chapter_extension = None

    def __init__(self):
        assert self.extension is not None
        assert self.name is not None

    def url(self, story):
        return url_for(
            'story.download',
            story_id=story.id,
            filename=slugify(story.title or str(story.id)) + '.' + self.extension,
        )

    def render(self, **kw):
        raise NotImplementedError

    @property
    def slug(self):
        return slugify(str(self.name.lower()))


class ZipFileDownloadFormat(BaseDownloadFormat):
    chapter_encoding = 'utf-8'

    def render(self, **kw):
        import zipfile
        from io import BytesIO

        buf = BytesIO()
        zf = zipfile.ZipFile(buf, mode='w', compression=zipfile.ZIP_DEFLATED)
        try:
            self.render_zip_contents(zf, **kw)
        finally:
            zf.close()

        return buf.getvalue()

    def render_zip_contents(self, zipfile, story, filename, **kw):
        from mini_fiction.models import Chapter

        ext = self.chapter_extension

        chapters = story.chapters.select().order_by(Chapter.order, Chapter.id)[:]
        num_width = len(str(len(chapters)))
        for i, chapter in enumerate(chapters):
            data = render_template(
                self.chapter_template,
                chapter=chapter,
                story=story,
            ).encode(self.chapter_encoding)

            name = slugify(chapter.autotitle)
            num = str(i + 1).rjust(num_width, '0')
            arcname = str('%s/%s_%s.%s' % (filename, num, name, ext))

            zipfile.writestr(arcname, data)


def slugify(s):
    from mini_fiction.utils.unidecode import unidecode
    return re.subn(r'\W+', '_', unidecode(s))[0]
