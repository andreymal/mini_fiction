#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from datetime import datetime

from flask import Markup, current_app

from .typographus import typo
from .base import html_doc_to_string, html_doc_transform, transform_xslt_params
from .html import normalize_html, footnotes_to_html


empty_lines_re = re.compile(r'\n[\s\n]*\n')


def filter_html(text, tags=None, attributes=None):
    if tags is None:
        tags = current_app.config['ALLOWED_TAGS']
    if attributes is None:
        attributes = current_app.config['ALLOWED_ATTRIBUTES']
    text = typo(text)
    doc = normalize_html(text, convert_linebreaks=True)
    doc = _filter_html(
        doc,
        tags=tags,
        attributes=attributes
    )
    return doc


def filtered_html_property(name, filter_):
    def fn(self):
        try:
            return Markup(html_doc_to_string(filter_(getattr(self, name) or '')))
        except Exception:
            import sys
            import traceback
            print(datetime.now().strftime('[%Y-%m-%d %H:%M:%S]'), "filter_html failed", type(self).__name__, self.get_pk(), name, filter_, file=sys.stderr)
            traceback.print_exc()
            return "#ERROR#"
    return property(fn)


_filter_transforms = {}


@html_doc_transform
def _filter_html(doc, tags, attributes, **kw):
    key = repr((tags, attributes))

    if key not in _filter_transforms:
        filters = []
        filters.extend(tags)
        for tag, attrs in attributes.items():
            for attr in attrs:
                filters.append('%s/@%s' % (tag, attr))
        filters = '|'.join(filters)
        data = HTML_FILTER_TEMPLATE.replace('@FILTERS@', filters)

        from lxml import etree
        _filter_transforms[key] = etree.XSLT(etree.XML(data))
    filter_transform = _filter_transforms[key]

    kw = transform_xslt_params(kw)
    return filter_transform(doc, **kw).getroot()


HTML_FILTER_TEMPLATE = """<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:re="http://exslt.org/regular-expressions">

<xsl:template match="html | body | @FILTERS@">
    <xsl:apply-templates select="." mode="default-filters"/>
</xsl:template>

<xsl:template match="@*"/>

<xsl:template match="img/@src[not(re:match(.,'^((https?:)?/|#)'))]" mode="default-filters"/>

<xsl:template match="a/@href[not(re:match(.,'^((https?:)?/|#)'))]" mode="default-filters"/>

<xsl:template match="@*|node()" mode="default-filters">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>

</xsl:stylesheet>
"""
