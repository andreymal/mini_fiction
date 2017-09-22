#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re


class BaseTextLinter:
    def __init__(self, text=None):
        self.text = text

    def lint(self):
        raise NotImplementedError

    def get_error_messages(self, error_codes=None):
        raise NotImplementedError


class DefaultChapterLinter(BaseTextLinter):
    BAD_PARAGRAPHS_SEP = 0
    TOO_FEW_PARAGRAPHS = 1
    BAD_DASHES = 2

    _pre_re = re.compile(r'<pre>.+?</pre>', re.DOTALL | re.M | re.I)
    _p_re = re.compile(r'</p>\s*<p.*?>', re.M | re.I)
    _newlines_re = re.compile(r'\n(\s*\n)+', re.M)
    _goods_re = re.compile(r'\n\n\S', re.M)

    def __init__(self, text=None):  # pylint: disable=W0235; false positive
        super().__init__(text)

    def lint(self):
        error_codes = set()

        if not self.text or len(self.text) < 2500:
            # Слишком короткие тексты проверять смысла мало
            return error_codes

        # Для начала проводим некоторую нормализацию текста для упрощения обработки

        # Убираем всё внутри pre: там обычные правила не действуют
        text = self._pre_re.sub('\n', self.text)
        # Нормализуем пробельные символы для удобства
        text = text.replace('&nbsp;', ' ').replace('&nbsp', ' ').replace('\xa0', ' ').replace('\t', '    ')
        # Заменяем разделение абзацев через <p> на пустую строку
        text = self._p_re.sub('\n\n', text)
        # Более чем одну пустую строку приводим к одной пустой строке (попутно убирая лишние пробельные символы)
        text = self._newlines_re.sub('\n\n', text)

        # Считаем число нормально оформленных абзацев (точнее, число правильных пустых строк)
        goods = len(self._goods_re.findall(text))

        # Пытаемся определить, не пытается ли писатель имитировать красную строку пробелами
        bads = text.count('\n   ') + text.count('<p>   ')
        bads += 1 if text.startswith('   ') else 0
        bads += 1 if text.startswith('<p>   ') else 0

        if bads >= 3 and goods/bads < 3:
            # Если плохих абзацев хотя бы в три раза больше чем хороших, то вопим о проблеме
            error_codes.add(self.BAD_PARAGRAPHS_SEP)
        else:
            # Если имитации красных строк нет, то проверяем, что есть хоть какое-то деление на абзацы
            if goods < 1 and text.count('<p>') == 0 and text.count('<p ') == 0 and text.count('\n\n') == 0:
                error_codes.add(self.TOO_FEW_PARAGRAPHS)

        # Ловим имитацию тире двумя дефисами
        dashes = text.count(' -- ') + text.count('\n-- ')
        if dashes >= 4:
            error_codes.add(self.BAD_DASHES)

        return error_codes

    def get_error_messages(self, error_codes=None):
        if error_codes is None:
            if self.text is None:
                raise ValueError('Please set "text" or "error_codes" before using "get_error_messages"')
            error_codes = self.lint()

        result = {}

        if self.BAD_PARAGRAPHS_SEP in error_codes:
            result[self.BAD_PARAGRAPHS_SEP] = (
                'Похоже, вы пытаетесь имитировать красную строку с помощью '
                'пробелов в начале первой строки абзаца. Не стоит делать '
                'так: разделяйте абзацы пустой строкой между ними. При '
                'чтении главы сайт даёт возможность выбрать предпочтительный '
                'читателем способ разделения абзацев.'
            )

        if self.TOO_FEW_PARAGRAPHS in error_codes:
            result[self.TOO_FEW_PARAGRAPHS] = (
                'Текст главы технически содержит всего один очень длинный '
                'абзац. Рекомендуется разбить текст на абзацы с помощью '
                'пустых строк. Обратите внимание, что простой перенос строки '
                'или пробелы в начале строки не считаются за новый абзац.'
            )

        if self.BAD_DASHES in error_codes:
            result[self.BAD_DASHES] = (
                'В тексте главы часто встречаются два дефиса подряд «--». '
                'Обычно таким образом пытаются имитировать тире «—», и вместо '
                'двух дефисов предпочтительнее использовать собственно тире. '
                'Для удобства ввода тире, а также других специальных символов '
                'вроде кавычек-«ёлочек» рекомендуем использовать '
                '<a href="https://ilyabirman.ru/projects/typography-layout/" target="_blank">'
                'типографскую раскладку'
                '</a>.'
            )

        return result


def create_chapter_linter(text=None):
    import importlib
    from flask import current_app

    if not current_app.config.get('CHAPTER_LINTER'):
        return None

    module_name, class_name = current_app.config['CHAPTER_LINTER'].rsplit('.', 1)

    module_obj = importlib.import_module(module_name)
    return getattr(module_obj, class_name)(text)
