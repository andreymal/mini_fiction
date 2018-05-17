#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from lxml import etree
import lxml.html.defs
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
