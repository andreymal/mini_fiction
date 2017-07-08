#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .base import ZipFileDownloadFormat


class FB2Download(ZipFileDownloadFormat):
    extension = 'fb2.zip'
    name = 'FB2'
    debug_content_type = 'text/xml'

    def render_fb2(self, story, **kw):
        import lxml.etree as etree
        from ..filters import fb2
        from mini_fiction.models import Chapter

        chapters = story.chapters.select().order_by(Chapter.order, Chapter.id)
        chapters = [fb2.html_to_fb2(c.get_filtered_chapter_text(), title=c.autotitle) for c in chapters]
        chapters = [self._get_annotation_doc(story)] + chapters

        doc = fb2.join_fb2_docs(
            chapters,
            title=story.title,
            author_name=story.authors[0].username,  # TODO: multiple authors
        )
        return etree.tostring(doc, encoding='UTF-8', xml_declaration=True)

    def render_zip_contents(self, zipfile, filename, **kw):
        data = self.render_fb2(**kw)
        zipfile.writestr(filename + '.fb2', data)

    def _get_annotation_doc(self, story):
        from ..filters import fb2

        doc = fb2.html_to_fb2('<annotation>%s</annotation>' % story.summary_as_html)
        for body in doc.xpath('//fb2:body', namespaces={'fb2': 'http://www.gribuser.ru/xml/fictionbook/2.0'}):
            body.getparent().remove(body)

        return doc

    def render(self, **kw):
        if kw.get('debug'):
            return self.render_fb2(**kw)
        else:
            return super(FB2Download, self).render(**kw)
