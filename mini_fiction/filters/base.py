#!/ust/bin/env python
# -*- coding: utf-8 -*-

import os
from functools import wraps

from lxml import etree
from flask import current_app


def load_xslt_transform(file_path):
    with open(file_path, 'rb') as f:
        return etree.XSLT(etree.XML(f.read(), base_url=file_path))


def html_doc_transform(fn):
    @wraps(fn)
    def wrapper(doc, **kw):
        if isinstance(doc, str):
            doc = etree.HTML('<body>' + doc + '</body>')
        return fn(doc, **kw)
    return wrapper


def html_text_transform(fn):
    @wraps(fn)
    def wrapper(doc):
        if not isinstance(doc, str):
            doc = html_doc_to_string(doc)
        return fn(doc)
    return wrapper


def transform_xslt_params(kw):
    for key, value in kw.items():
        if isinstance(value, str):
            value = etree.XSLT.strparam(value)
        elif isinstance(value, bool):
            value = 'true()' if value else 'false()'
        elif isinstance(value, (int, float)):
            value = str(value)
        else:
            raise TypeError(key)
        kw[key] = value
    return kw


def xslt_transform_loader(file_path):
    dir_path = os.path.dirname(file_path)

    def factory(xslt_name):
        xslt_path = os.path.join(dir_path, xslt_name)

        if False and not current_app.config['DEBUG']:  # FIXME: can't port this
            transform_ = load_xslt_transform(xslt_path)

            def transform(doc, **kw):
                kw = transform_xslt_params(kw)
                return transform_(doc, **kw).getroot()
        else:
            def transform(doc, **kw):
                kw = transform_xslt_params(kw)
                transform = load_xslt_transform(xslt_path)
                return transform(doc, **kw).getroot()

        return html_doc_transform(transform)
    return factory


def html_doc_to_string(doc):
    if isinstance(doc, str):
        return doc

    body = doc.xpath('//body')
    if len(body) < 1:
        return ''
    body = body[0]
    doc = ''.join([(body.text or '')] + [etree.tounicode(elem, method='html') for elem in body.getchildren()])
    return doc
