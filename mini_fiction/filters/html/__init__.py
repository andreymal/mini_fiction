#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from lxml import etree
import lxml.html.defs

from mini_fiction.utils.misc import make_absolute_url
from ..base import xslt_transform_loader, html_doc_transform

xslt_transform_function = xslt_transform_loader(__file__)

footnotes_to_html = xslt_transform_function('footnotes.xslt')

pre_normalize_html = xslt_transform_function('pre-normalize-html.xslt')
post_normalize_html = xslt_transform_function('post-normalize-html.xslt')

default_block_elements = (lxml.html.defs.block_tags | frozenset(['footnote', 'body'])) - frozenset(['p'])


@html_doc_transform
def normalize_html(doc, block_elements=default_block_elements, **kw):
    for e in doc.xpath('//' + '|//'.join(block_elements)):
        e.attrib['block-element'] = 'true'

    # prevent adding extra <br/>
    for e in doc.xpath('//p|//br|//' + '|//'.join(block_elements)):
        # before block elements
        prev_e = e.getprevious()
        if prev_e is not None and prev_e.tail:
            # use case: "foo<br/>foo\n\nbar\n\n<ul><li>baz</li></ul>"
            prev_e.tail = re.sub(r'\n\s*$', '', prev_e.tail)
        elif prev_e is None:
            # use case: "<body>foo\n\n<p>bar</p>\n\nbaz</body>"
            parent = e.getparent()
            if parent is not None and parent.text:
                parent.text = re.sub(r'\n\s*$', '', parent.text)

        # inside block elements
        if e.text:
            # use case: "<p>\n\nfoo\n\n</p>"
            e.text = re.sub(r'^\s*\n', '', e.text)
            # have in mind: "<body>\n\nfoo\n\n<img/>\n\n</body>"
            if len(e.getchildren()) == 0:
                e.text = re.sub(r'\n\s*$', '', e.text)

        # and after block elements
        if e.tail:
            # use case: "<p>foo</p>\n\nbar"
            e.tail = re.sub(r'^\s*\n', '', e.tail)

    doc = pre_normalize_html(doc, **kw)
    doc = split_elements(
        doc,
        separators=['p-splitter'],
        block_elements=block_elements
    )
    squash_paragraph_attributes(doc)
    doc = post_normalize_html(doc, **kw)

    for img in doc.xpath('//img'):
        if not img.get('alt'):
            img.set('alt', '')

    # Make all links absolute (required for downloaded files)
    make_html_links_absolute(doc)

    return doc


@html_doc_transform
def split_elements(doc, separators=None, block_elements=lxml.html.defs.block_tags):
    block_elements = (block_elements | frozenset(['body'])) - frozenset(['p'])
    for body in doc.xpath('//body'):
        list(iter_splitted_elements(body, separators or [], block_elements))
    return doc


def iter_splitted_elements(element, separators, block_elements):
    children = element.getchildren()
    if len(children) == 0:
        yield element
        return

    tag = element.tag
    # Костыль: кривые теги (например, '...') заменяем на 'span'
    if not re.match(r'^[A-Za-z0-9-]+$', tag):
        tag = 'span'

    if tag in block_elements:
        children = element[:]
        element[:] = []
        element.extend(f
            for e in children
            for f in iter_splitted_elements(e, separators, block_elements)
        )
        yield element
        return

    attrib = dict(element.attrib)
    accum = []
    for d in children:
        for e in iter_splitted_elements(d, separators, block_elements):
            if e.tag in separators:
                if len(accum) > 0:
                    x = etree.Element(tag, attrib)
                    x.extend(accum)
                    yield x
                    accum = []
                yield e
            else:
                accum.append(e)
    x = etree.Element(tag, attrib)
    x.extend(accum)
    yield x


def squash_paragraph_attributes(doc):
    for p in doc.xpath('//p'):
        for np in p.xpath('.//p'):
            p.attrib.update(dict(np.attrib))
    return doc


def make_html_links_absolute(doc):
    for img in doc.xpath('.//img'):
        if img.get('src'):
            img.set('src', make_absolute_url(img.get('src')))
    for a in doc.xpath('.//a'):
        if a.get('href'):
            a.set('href', make_absolute_url(a.get('href')))
