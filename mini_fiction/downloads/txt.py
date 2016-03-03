#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .base import ZipFileDownloadFormat


class TXTDownload(ZipFileDownloadFormat):
    extension = 'txt.utf8.zip'
    name = u'TXT (кодировка Unicode)'
    chapter_template = 'chapter_pure_text.txt'
    chapter_extension = 'txt'
    slug = 'txt'


class TXT_CP1251Download(TXTDownload):
    extension = 'txt.win.zip'
    name = 'TXT (кодировка Windows)'
    chapter_encoding = 'cp1251'
