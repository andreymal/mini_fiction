#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import zipfile

from flask import url_for, render_template
from mini_fiction.utils import misc


class BaseDownloadFormat(object):
    extension = None
    name = None
    content_type = 'application/octet-stream'
    debug_content_type = 'text/plain; charset=utf-8'
    chapter_template = None
    chapter_extension = None

    def __init__(self, slugify_filenames=False):
        assert self.extension is not None
        assert self.name is not None
        self.slugify_filenames = bool(slugify_filenames)

    def url(self, story):
        return url_for(
            'story.download',
            story_id=story.id,
            filename=self.filename(story),
        )

    def filename(self, story):
        title = (story.title or str(story.id)).strip().replace('.', '')
        if self.slugify_filenames:
            title = slugify(title)
        else:
            title = misc.sanitize_filename(title, strip=True)
        return '{}.{}'.format(title, self.extension)

    def render(self, **kw):
        raise NotImplementedError

    @property
    def slug(self):
        return slugify(str(self.name.lower()))


class ZipFileDownloadFormat(BaseDownloadFormat):
    content_type = 'application/zip'
    chapter_encoding = 'utf-8'

    def render(self, **kw):
        from io import BytesIO

        buf = BytesIO()
        zipobj = zipfile.ZipFile(buf, mode='w', compression=zipfile.ZIP_DEFLATED)
        try:
            self.render_zip_contents(zipobj, **kw)
        finally:
            zipobj.close()

        return buf.getvalue()

    def render_zip_contents(self, zipobj, story, **kw):
        from mini_fiction.models import Chapter

        dirname = slugify(story.title or str(story.id))
        ext = self.chapter_extension

        chapters = list(story.chapters.select(lambda x: not x.draft).order_by(Chapter.order, Chapter.id))
        num_width = len(str(max(x.order for x in chapters))) if chapters else 1
        for chapter in chapters:
            data = render_template(
                self.chapter_template,
                chapter=chapter,
                story=story,
            ).encode(self.chapter_encoding)

            name = slugify(chapter.autotitle)
            num = str(chapter.order).rjust(num_width, '0')
            arcname = str('%s/%s_%s.%s' % (dirname, num, name, ext))

            zipdate = chapter.updated
            if chapter.first_published_at and chapter.first_published_at > zipdate:
                zipdate = chapter.first_published_at
            zipinfo = zipfile.ZipInfo(
                arcname,
                date_time=zipdate.timetuple()[:6],
            )
            zipinfo.compress_type = zipfile.ZIP_DEFLATED
            zipinfo.external_attr = 0o644 << 16  # Python 3.4 ставит файлам права 000, фиксим

            zipobj.writestr(zipinfo, data)


def slugify(s):
    from mini_fiction.utils.unidecode import unidecode
    return re.subn(r'\W+', '_', unidecode(s))[0]
