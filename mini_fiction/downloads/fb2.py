#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zipfile

from .base import BaseDownloadFormat, ZipFileDownloadFormat, slugify


class FB2BaseDownload:
    def render_fb2(self, story, **kw):
        import lxml.etree as etree
        from ..filters import fb2
        from mini_fiction.models import Chapter

        chapters = story.chapters.select(lambda x: not x.draft).order_by(Chapter.order, Chapter.id)
        chapters = [fb2.html_to_fb2(c.get_fb2_chapter_text(), title=c.autotitle) for c in chapters]
        subdocs = [self._get_annotation_doc(story)] + chapters

        doc = fb2.join_fb2_docs(
            subdocs,
            title=story.title,
            author_name=story.authors[0].username,  # TODO: multiple authors
            date=(story.first_published_at or story.date).strftime('%Y-%m-%dT%H:%M:%SZ'),
        )
        return etree.tostring(doc, encoding='UTF-8', xml_declaration=True)

    def _get_annotation_doc(self, story):
        from ..filters import fb2

        if story.notes:
            html = '<annotation>%s%s</annotation>' % (story.summary_as_html, story.notes_as_html)
        else:
            html = '<annotation>%s</annotation>' % story.summary_as_html
        doc = fb2.html_to_fb2(html)
        for body in doc.xpath('//fb2:body', namespaces={'fb2': 'http://www.gribuser.ru/xml/fictionbook/2.0'}):
            body.getparent().remove(body)

        return doc


class FB2Download(FB2BaseDownload, BaseDownloadFormat):
    extension = 'fb2'
    name = 'FB2'
    content_type = 'application/x-fictionbook+xml; charset=utf-8'
    debug_content_type = 'text/xml; charset=utf-8'

    def render(self, **kw):
        return self.render_fb2(**kw)


class FB2ZipDownload(FB2BaseDownload, ZipFileDownloadFormat):
    extension = 'fb2.zip'
    name = 'FB2+zip'
    content_type = 'application/x-zip-compressed-fb2'
    debug_content_type = 'text/xml; charset=utf-8'

    def render_zip_contents(self, zipobj, story, **kw):
        data = self.render_fb2(story=story, **kw)

        filename = kw.pop('filename', slugify(story.title or str(story.id))) + '.fb2'

        zipinfo = zipfile.ZipInfo(
            filename,
            date_time=story.updated.timetuple()[:6],
        )
        zipinfo.compress_type = zipfile.ZIP_DEFLATED
        zipinfo.external_attr = 0o644 << 16  # Python 3.4 ставит файлам права 000, фиксим

        zipobj.writestr(zipinfo, data)

    def render(self, **kw):
        if kw.get('debug'):
            return self.render_fb2(**kw)
        return super().render(**kw)
