#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def split_words(s):
    '''Разделяет текст на слова по-умному для подсчёта различий.'''

    ALPHA = 1
    SPACE = 2
    OTHER = 0

    result = []
    last = OTHER
    tag = False

    for char in s:
        # Определяем тип символа
        current = OTHER
        if char.isspace():
            current = SPACE
        elif char.isalpha() or char.isdigit():
            current = ALPHA

        if char == '\n':
            # Символ новой строки всегда отдельно
            result.append(char)
            tag = False

        elif current == SPACE:
            # После слова без знака препинания оставляем один пробел, всё остальное отдельно
            if tag or not result or last == SPACE or last == OTHER:
                result.append(char)
                tag = False
            else:
                result[-1] += char

        elif char == '<':
            # html-теги обрабатываем особым образом, чтоб слишком мелко не дробить
            result.append(char)
            tag = True

        elif tag and (current == ALPHA or char == '=' or char == '/' or char == '>'):
            # Буквы и некоторые спецсимволы в html-теге объединяем
            result[-1] += char
            if char == '>':
                tag = False

        elif current != OTHER and current == last:
            # Буквы и цифры, идущие подряд, объединяем
            result[-1] += char

        elif current == OTHER and last == ALPHA and char in '.,?!:;':
            # После слова оставляем знак препинания (и пробел в следующей итерации)
            result[-1] += char

        else:
            # Всё остальное просто добавляем как новое слово
            result.append(char)
            tag = False

        last = current

    return result


def get_diff_default(a, b):
    '''Возвращает различия между строками ``a`` и ``b`` в виде списка.
    Каждый элемент списка — кортеж из двух элментов, который показывает
    действие, которое нужно применить к ``a``, чтобы получить ``b``:

    - ``('=', длина)`` — кусок указанной длины одинаков для ``a`` и ``b``

    - ``('+', 'кусок')`` — этот кусок добавлен в новом тексте

    - ``('-', 'кусок')`` — этот кусок удалён из старого текста

    Используется встроенный класс Python ``difflib.SequenceMatcher``, который
    иногда медленный.
    '''

    from difflib import SequenceMatcher

    a = split_words(a)
    b = split_words(b)

    result = []

    s = SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in s.get_opcodes():
        if op == 'equal':
            result.append(('=', len(''.join(a[i1:i2]))))
        if op == 'delete' or op == 'replace':
            result.append(('-', ''.join(a[i1:i2])))
        if op == 'insert' or op == 'replace':
            result.append(('+', ''.join(b[j1:j2])))

    return result


def get_diff_google(a, b):
    '''Возвращает различия между строками ``a`` и ``b`` в виде списка.
    Каждый элемент списка — кортеж из двух элментов, который показывает
    действие, которое нужно применить к ``a``, чтобы получить ``b``:

    - ``('=', длина)`` — кусок указанной длины одинаков для ``a`` и ``b``

    - ``('+', 'кусок')`` — этот кусок добавлен в новом тексте

    - ``('-', 'кусок')`` — этот кусок удалён из старого текста

    Используется ``google-diff-match-patch``, который быстрый, но даёт
    не самые красивые диффы.
    '''

    import diff_match_patch

    ia = 0
    ib = 0

    result = []

    for op, l in diff_match_patch.diff(a, b, timelimit=20, checklines=False):
        if op == '=':
            assert a[ia:ia + l] == b[ib:ib + l]
            result.append(('=', l))
            ia += l
            ib += l
        elif op == '-':
            result.append(('-', a[ia:ia + l]))
            ia += l
        elif op == '+':
            result.append(('+', b[ib:ib + l]))
            ib += l

    return result


def apply_diff(a, diff):
    '''Применяет дифф, подсчитанный функциями ``get_diff``, к старому тексту
    для получения нового.

    :param str a: старый текст
    :param list diff: дифф для получения нового текста из старого
    :return: новый текст
    :rtype: str
    '''

    i = 0
    result = []
    for op, data in diff:
        if op == '=':
            result.append(a[i:i + data])
            i += data
        elif op == '+':
            result.append(data)
        elif op == '-':
            assert a[i:i + len(data)] == data
            i += len(data)

    return ''.join(result)


def revert_diff(b, diff):
    '''Применяет дифф, подсчитанный функциями ``get_diff``, к новому тексту
    для получения старого. Другими словами, откатывает данный дифф.

    :param str b: новый текст
    :param list diff: дифф для получения нового текста из старого (sic!)
    :return: старый текст
    :rtype: str
    '''

    i = 0
    result = []
    for op, data in diff:
        if op == '=':
            result.append(b[i:i + data])
            i += data
        elif op == '-':
            result.append(data)
        elif op == '+':
            assert b[i:i + len(data)] == data
            i += len(data)

    return ''.join(result)
