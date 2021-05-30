import re
from dataclasses import dataclass
from typing import Any, Optional, List, Callable
from urllib.parse import parse_qs

from flask import current_app


@dataclass
class TextContainer:
    changed: bool
    flags: List[str]
    text: str


star_begin = r'\s*\n\s*(<(p|span)( align="?[a-z]+"?)?>|<strong>|<b>|<em>|<i>|<center>|<h[1-6]>)*(\s|&nbsp;)*'
star_end = r"(\s|&nbsp;)*(</p>|</span>|</strong>|</b>|</em>|</i>|</center>|</h[1-6]>)*(</?br\s*/?>)?\s*\n\s*"


html_entities_table = {
    "laquo": "«",
    "raquo": "»",
    "mdash": "—",
    "aacute": "á",
    "ac": "∾",
    "acirc": "â",
    "agrave": "à",
    "bdquo": "„",
    "bull": "•",
    "copy": "©",
    "eacute": "é",
    "ecirc": "ê",
    "hellip": "…",
    "iacute": "í",
    "iexcl": "¡",
    "iquest": "¿",
    "ldquo": "“",
    "lsquo": "‘",
    "middot": "·",
    "minus": "−",
    "ndash": "–",
    "not": "¬",
    "ntilde": "ñ",
    "oacute": "ó",
    "ouml": "ö",
    "prime": "′",
    "rdquo": "”",
    "rsquo": "’",
    "szlig": "ß",
    "times": "×",
    "uacute": "ú",
    "uuml": "ü",
}


def repeat(func: Callable[..., str], old_text: str, *args: Any, **kwargs: Any) -> str:
    """
    Повторяет указанную функцию несколько раз до тех пор, пока она
    не перестанет вносить новые изменения.
    """

    old_new_text = old_text
    count = 0
    while count <= 100:
        new_text = func(old_new_text, *args, **kwargs)
        if new_text == old_new_text:
            return new_text
        count += 1
        old_new_text = new_text

    raise RuntimeError(f"Function {func.__name__} repeated more than 100 times")


def fix_invalid_br(old_text: str, flags: List[str]) -> str:
    """
    Исправляет </br> на <br/>.
    """
    new_text = re.sub(r"(<br\s*/?>)?</br>", "<br/>", old_text, flags=re.I | re.M)
    if new_text != old_text:
        flags.append("invalid_br")
    return new_text


def fix_useless_p(old_text: str, flags: List[str]) -> str:
    """
    Исправляет бесполезные <p></p> в началах и концах строк. Потенциально
    полезные (например, добавляющие пустые строки) старается не трогать.
    """
    new_text = re.sub(
        r"\s*\n\s*<p></p> *([A-Za-z0-9А-Яа-яЁё—–\.\-])",
        "\n\n\\1",
        old_text,
        flags=re.I | re.M,
    )
    new_text = re.sub(
        r"([A-Za-z0-9А-Яа-яЁё—–\.\-]) *<p></p>\s*\n\s*",
        "\\1\n\n",
        new_text,
        flags=re.I | re.M,
    )
    if new_text != old_text:
        flags.append("useless_p")
    return new_text


def fix_stars(old_text: str, flags: List[str]) -> str:
    """
    Исправляет звёздочки на <hr/>, попутно удаляя заворачивание его
    в мусорные теги.
    """
    new_text = re.sub(
        star_begin + r"\*+\s*\*+\s*[ \*]+" + star_end,
        "\n\n<hr/>\n\n",
        old_text,
        flags=re.I | re.M,
    )
    if new_text != old_text:
        flags.append("stars")
    return new_text


def fix_stars2(old_text: str, flags: List[str]) -> str:
    """
    Тоже исправляет звёздочки на <hr/>, но специальная версия для ситуации вида
    <span align="center"></span>* * *
    """
    new_text = re.sub(
        (
            r'\s*<(p|span)( align="?[a-z]+"?)?>\s*</(p|span)>\s*'
            r"\*+\s*\*+\s*[ \*]+"
            r'\s*'
        ),
        "\n\n<hr/>\n\n",
        old_text,
        flags=re.I | re.M,
    )
    if new_text != old_text:
        flags.append("stars2")
    return new_text


def fix_extra_hr(old_text: str, flags: List[str]) -> str:
    """
    Заменяет другие звёздочкоподобные образования на <hr/>.
    """
    new_text2 = new_text = old_text

    if "=" in new_text:
        new_text2 = re.sub(
            star_begin + r"\=+ *\=+ *\=+[ \=]*" + star_end,
            "\n\n<hr/>\n\n",
            new_text,
            flags=re.I | re.M,
        )
        if new_text2 != new_text:
            flags.append("hr_eq")

    new_text = new_text2
    if "-" in new_text:
        new_text2 = re.sub(
            star_begin + r"\-+ *\-+ *\-+[ \-]*" + star_end,
            "\n\n<hr/>\n\n",
            new_text,
            flags=re.I | re.M,
        )
        if new_text2 != new_text:
            flags.append("hr_hyphen")

    return new_text2


def fix_hr_wrapped(old_text: str, flags: List[str]) -> str:
    """
    Убирает заворачивание <hr/> в бесполезные strong и em (такое может случиться
    после работы предыдущих функций).
    """
    new_text = re.sub(
        r"\s*(<strong>|<em>)+\s*<hr\s*/?>\s*(</strong>|</em>)+\s*",
        "\n\n<hr/>\n\n",
        old_text,
        flags=re.I | re.M,
    )
    if new_text != old_text:
        flags.append("hr_wrapped")

    return new_text


def fix_hr_spaces(old_text: str, flags: List[str]) -> str:
    """
    Нормализует пробельные символы между несколькими <hr/> идущими подряд.
    """
    new_text = old_text

    while True:
        new_text2 = re.sub(
            r"<hr\s*/?>\s*<hr\s*/?>\s*",
            "<hr/>\n<hr/>\n",
            new_text,
            flags=re.M | re.I,
        )
        if new_text2 == new_text:
            break
        new_text = new_text2

    new_text = re.sub(
        r"\s*((<hr/>\n)+)\s*",
        "\n\n\\1\n",
        new_text,
        flags=re.M,
    )

    if new_text != old_text:
        flags.append("hr_spaces")
    return new_text


def fix_headers(old_text: str, flags: List[str]) -> str:
    """
    Исправляет все заголовки на <h3>.
    """
    new_text = re.sub(
        r"\s*<h[12456]>(.+?)</h[12456]>\s*",
        "\n\n<h3>\\1</h3>\n\n",
        old_text,
        flags=re.I | re.M,
    )
    if new_text != old_text:
        flags.append("headers")
    return new_text


def fix_footnotes_hr(old_text: str, flags: List[str]) -> str:
    """
    Убирает ненужный <hr/> перед <footnote>, так как в новой версии фронтенда
    разделительная линия рисуется через CSS.
    """
    new_text = re.sub(
        r"\s*<hr\s*/?>\s*<footnote",
        "\n\n<footnote",
        old_text,
        flags=re.I | re.M,
    )
    if new_text != old_text:
        flags.append("footnotes_hr")
    return new_text


def fix_span_align(old_text: str, flags: List[str]) -> str:
    """
    Переделывает <span align="center|right"> в <p align="center|right">.
    """
    new_text = re.sub(
        r'\s*<span\s+align="?([a-z]+)"?>(.+?)</span>\s*',
        '\n\n<p align="\\1">\\2</p>\n\n',
        old_text,
        flags=re.I | re.M | re.DOTALL,
    )
    if new_text != old_text:
        flags.append("span_align")
    return new_text


def fix_double_align(old_text: str, flags: List[str]) -> str:
    """
    Убирает двойное выравнивание.
    """
    new_text = re.sub(
        r'\s*<p align="?([a-z]+?)"?>\s*<p align="?[a-z]+?"?>(.+?)</p>\s*</p>\s*',
        '\n\n<p align="\\1">\\2</p>\n\n',
        old_text,
        flags=re.I | re.M | re.DOTALL,
    )
    if new_text != old_text:
        flags.append("double_align")
    return new_text


def fix_align_left(old_text: str, flags: List[str]) -> str:
    """
    Удаляет бесполезный <p align="left">.
    """
    new_text = re.sub(
        r'\s*<p\s+align="?left"?>\s*(\S+?)\s*</p>\s*',
        "\n\n\\1\n\n",
        old_text,
        flags=re.I | re.M,
    )
    if new_text != old_text:
        flags.append("align_left")
    return new_text


def fix_ficbook_block(old_text: str, flags: List[str]) -> str:
    """
    Заменяет фикбуковые блочные теги на эквиваленты из ванильного html.
    """
    new_text = old_text

    for x1, x2 in [
        (r"\s*<(right|center)>", '\n\n<p align="\\1">'),
        (r"</(right|center)>\s*", "</p>\n\n"),
        (r"\s*<tab\s*/?>\s*", "\n\n"),
    ]:
        new_text = re.sub(x1, x2, new_text, flags=re.I)

    if new_text != old_text:
        flags.append("ficbook_block")
    return new_text


def fix_strong_em(old_text: str, flags: List[str]) -> str:
    """
    Заменяет b/i на strong/em.
    """
    new_text = old_text

    for x1, x2 in [
        ("<i>", "<em>"),
        ("</i>", "</em>"),

        ("<b>", "<strong>"),
        ("</b>", "</strong>"),
    ]:
        new_text = re.sub(x1, x2, new_text, flags=re.I | re.M)

    if new_text != old_text:
        flags.append("strong_em")
    return new_text


def fix_double_tags(old_text: str, flags: List[str]) -> str:
    """
    Устраняет дубликаты тегов вида <em><em></em></em>. Такое могло случаться
    при двойном клике на кнопку в редакторе или при копировании текста из Word.
    """
    new_text = old_text

    while True:
        new_text2 = re.sub(
            r"<(strong|em|h3)>(\s*)<\1>(.+?)</\1>(\s*)</\1>",
            "<\\1>\\2\\3\\4</\\1>",
            new_text,
            flags=re.I | re.M
        )
        if new_text2 == new_text:
            break
        new_text = new_text2

    if new_text != old_text:
        flags.append("double_tags")
    return new_text


def fix_empty_tags(old_text: str, flags: List[str]) -> str:
    """
    Удаляет пустые теги, которые ничего не делают. Не удаляет <p></p>,
    потому что он может присутствовать специально для добавления пустой строки.
    """
    new_text = re.sub(
        r"<(strong|em|s|u|sup|sub|small|h3)></\1>",
        "",
        old_text,
        flags=re.I,
    )

    if new_text != old_text:
        flags.append("empty_tags")
    return new_text


def fix_union_tags(old_text: str, flags: List[str]) -> str:
    """
    Объединяет соседствующие одинаковые теги вида <em></em><em></em>, если это
    не влияет на отображение или семантику текста.
    """
    new_text = re.sub(
        r"</(s|u|small)><\1>",
        "",
        old_text,
        flags=re.I,
    )

    new_text = re.sub(
        r"</(strong|em|sup|sub)>( *)<\1>",
        r"\2",
        new_text,
        flags=re.I,
    )

    if new_text != old_text:
        flags.append("union_tags")
    return new_text


def fix_empty_a(old_text: str, flags: List[str]) -> str:
    """
    Удаляет пустые теги <a></a>, которые могли случайно появиться
    при копировании из Word.
    """
    new_text = re.sub("<a>(.*?)</a>", "\\1", old_text, flags=re.I | re.M)
    if new_text != old_text:
        flags.append("empty_a")
    return new_text


def fix_tt2em(old_text: str, flags: List[str]) -> str:
    """
    Заменяет tt на em, потому что именно так «К лучшей жизни с наукой и пони»
    сверстали в бумаге.
    """
    new_text = re.sub("<tt>", "<em>", old_text, flags=re.I | re.M)
    new_text = re.sub("</tt>", "</em>", new_text, flags=re.I | re.M)

    if new_text != old_text:
        flags.append("tt2em")
    return new_text


def fix_leading_whitespace(old_text: str, flags: List[str]) -> str:
    """
    Удаляет пробельные символы в начале строк, так как они всё равно бесполезны.
    """
    new_text = re.sub(r"\n[ \t]+", "\n", old_text, flags=re.I | re.M)
    if new_text != old_text:
        flags.append("leading_whitespace")
    return new_text


def fix_trailing_whitespace(old_text: str, flags: List[str]) -> str:
    """
    Удаляет пробельные символы и &nbsp; в конце строк, так как они всё равно бесполезны.
    """
    new_text = re.sub(r"(\s|&nbsp;)+$", "\n", old_text, flags=re.I | re.M)
    if new_text != old_text:
        flags.append("trailing_whitespace")
    return new_text


def fix_html_entities(old_text: str, flags: List[str]) -> str:
    """
    Заменяет некоторые html-сущности на оригинальные символы. Не трогает
    &lt;, &gt;, &amp;, &quot;, &nbsp; и &shy;.
    """
    new_text = old_text

    entities = re.findall(r"&([A-Za-z]+)\b;?", new_text)
    for e in entities:
        e = e.lower()
        if e in html_entities_table:
            new_text = re.sub(r"&" + e + r"\b;?", html_entities_table[e], new_text, flags=re.I)

    if new_text != old_text:
        flags.append("html_entities")
    return new_text


def fix_trailing_br_p_and_spaces(old_text: str, flags: List[str]) -> str:
    """
    Убирает бесполезные пустые строки в конце текста.
    """

    # Маленький кусочек обрабатывается намного быстрее целого текста
    part1 = old_text[:-200]
    old_part2 = old_text[-200:]

    new_part2 = re.sub(r"(&nbsp;|\s|<br\s*/?>)+(</p>)?(\s|&nbsp;)*\Z", r"\2", old_part2, flags=re.I | re.M)
    new_part2 = re.sub(r"(\s|&nbsp;)*<p>(\s|&nbsp;)*</p>(\s|&nbsp;)*\Z", "", new_part2, flags=re.I | re.M)
    if new_part2 != old_part2:
        flags.append("trailing_br_p_and_spaces")
        return part1 + new_part2
    return old_text


def fix_p_unwrap(old_text: str, flags: List[str]) -> str:
    """
    Тексты некоторых глав полностью завёрнуты в один единственный <p></p> — эта
    функция удаляет его в связи с бесполезностью.
    """
    if old_text.count("<p") != 1:
        return old_text

    new_text = re.sub(r'\A\s*<p>\s*(.+)\s*</p>\s*\Z', r'\1', old_text, flags=re.I | re.M | re.DOTALL)
    if new_text != old_text:
        flags.append("p_unwrap")
    return new_text


def fix_links(old_text: str, flags: List[str]) -> str:
    """
    Проводит нормализацию некоторых видов ссылок.
    """
    new_text2 = new_text = old_text

    for camo_link in re.findall(r"https?://camo\.derpicdn\.net/[A-Za-z0-9_%?&\=\.\+\-]+", new_text2, flags=re.I):
        if "?" not in camo_link:
            continue
        uncamoed_link = parse_qs(camo_link.split("?", 1)[1])["url"][0]
        new_text2 = new_text2.replace(camo_link, uncamoed_link)
    if new_text2 != new_text:
        flags.append("links_camo_derpicdn")

    new_text = new_text2
    for camo_link in re.findall(r"https?://camo\.fimfiction\.net/[A-Za-z0-9_%?&\=\.\+\-]+", new_text2, flags=re.I):
        if "?" not in camo_link:
            continue
        uncamoed_link = parse_qs(camo_link.split("?", 1)[1])["url"][0]
        new_text2 = new_text2.replace(camo_link, uncamoed_link)
    if new_text2 != new_text:
        flags.append("links_camo_fimfiction")

    new_text = new_text2
    for camo_group in re.findall(r"(https?://(www\.)?vk\.com/away(\.php)?\?[A-Za-z0-9_%?&\=\.\+\_\-]+)", new_text2, flags=re.I):
        camo_link = camo_group[0]
        uncamoed_link = parse_qs(camo_link.split("?", 1)[1])["to"][0]
        new_text2 = new_text2.replace(camo_link, uncamoed_link)
    if new_text2 != new_text:
        flags.append("links_vk_away")

    new_text = new_text2
    new_text2 = new_text.replace("http://pp.vk.me/", "https://pp.userapi.com/")
    new_text2 = new_text2.replace("https://pp.vk.me/", "https://pp.userapi.com/")
    if new_text2 != new_text:
        flags.append("links_vk_me")

    new_text = new_text2
    new_text2 = new_text.replace("http://derpiboo.ru/", "https://derpibooru.org/")
    new_text2 = new_text2.replace("https://derpiboo.ru/", "https://derpibooru.org/")
    if new_text2 != new_text:
        flags.append("links_derpiboo_ru")

    new_text = new_text2
    new_text2 = new_text.replace("http://habrahabr.ru/", "https://habr.com/ru/")
    new_text2 = new_text2.replace("https://habrahabr.ru/", "https://habr.com/ru/")
    if new_text2 != new_text:
        flags.append("links_habrahabr")

    new_text = new_text2
    new_text2 = re.sub(
        r"https?://cs([0-9]+)\.(userapi\.com|vk\.me)/",
        "https://pp.userapi.com/c\\1/",
        new_text,
        flags=re.I,
    )
    if new_text2 != new_text:
        flags.append("links_vk")

    new_text = new_text2
    new_text2 = re.sub(
        r"https?://darkpony\.ru/",
        "https://darkpony.space/",
        new_text,
        flags=re.I,
    )
    if new_text2 != new_text:
        flags.append("links_darkpony_ru")

    return new_text2


def fix_double_http(old_text: str, flags: List[str]) -> str:
    """
    Исправляет присутствие двух протоколов в ссылках, что встречается
    в некоторых текстах.
    """

    new_text = old_text
    for _ in range(20):
        new_text2 = re.sub(r"(http://)+http://", "http://", new_text, flags=re.I)
        new_text2 = re.sub(r"(https?://)+https://([^h])", "https://\\2", new_text2, flags=re.I)
        if new_text2 != new_text:
            new_text = new_text2
        else:
            break

    if new_text != old_text:
        flags.append("double_http")

    return new_text


def fix_relative_links(old_text: str, flags: List[str]) -> str:
    """
    Меняет абсолютные ссылки на текущий сайт на относительные.
    """
    new_text: str = re.sub(
        r'(href|src)=("?)(https?:)?//(' + current_app.config['SERVER_NAME_REGEX'] + ')/',
        r"\1=\2/",
        old_text,
        flags=re.I,
    )
    if new_text != old_text:
        flags.append("relative_links")
    return new_text


def convert(old_text: str) -> TextContainer:
    new_text = "\n\n" + old_text.replace("\r", "") + "\n\n"
    ltext = new_text.lower()

    has_tags = "<" in new_text
    has_hr = has_tags and "<hr" in ltext
    has_html_entities = "&" in new_text
    has_links = "//" in new_text

    header_levels = 0
    if has_tags:
        header_levels = sum([
            "<h1" in ltext,
            "<h2" in ltext,
            "<h3" in ltext,
            "<h4" in ltext,
            "<h5" in ltext,
            "<h6" in ltext,
        ])

    flags: List[str] = []

    if has_tags:
        new_text = fix_invalid_br(new_text, flags)
        new_text = fix_useless_p(new_text, flags)
        new_text = repeat(fix_span_align, new_text, flags)
        new_text = repeat(fix_double_align, new_text, flags)

    # begin hr stuff

    new_text_hr = new_text
    if "*" in new_text_hr:
        new_text_hr = fix_stars(new_text_hr, flags)
        new_text_hr = fix_stars2(new_text_hr, flags)

    new_text_hr = fix_extra_hr(new_text_hr, flags)
    has_hr = has_hr or "<hr" in new_text_hr.lower()
    new_hr_added = new_text_hr != new_text

    if has_hr:
        new_text_hr = fix_hr_wrapped(new_text_hr, flags)
        if new_hr_added:
            new_text_hr = fix_hr_spaces(new_text_hr, flags)

    new_text = new_text_hr

    # end hr stuff

    if has_tags:
        if header_levels == 1:
            new_text = fix_headers(new_text, flags)

        if has_hr:
            new_text = fix_footnotes_hr(new_text, flags)
        new_text = fix_align_left(new_text, flags)
        new_text = fix_ficbook_block(new_text, flags)
        new_text = fix_strong_em(new_text, flags)
        new_text = fix_tt2em(new_text, flags)
        new_text = repeat(fix_empty_tags, new_text, flags)
        new_text = fix_empty_a(new_text, flags)
        new_text = repeat(fix_double_tags, new_text, flags)
        new_text = repeat(fix_union_tags, new_text, flags)

    new_text = fix_leading_whitespace(new_text, flags)
    new_text = fix_trailing_whitespace(new_text, flags)
    if has_html_entities:
        new_text = fix_html_entities(new_text, flags)

    if has_links:
        new_text = fix_links(new_text, flags)
        new_text = fix_relative_links(new_text, flags)

    new_text = new_text.strip()

    new_text = repeat(fix_trailing_br_p_and_spaces, new_text, flags)
    new_text = fix_p_unwrap(new_text, flags)

    if new_text == old_text.strip():
        return TextContainer(changed=False, flags=flags, text=new_text)

    return TextContainer(changed=True, flags=flags, text=new_text)
