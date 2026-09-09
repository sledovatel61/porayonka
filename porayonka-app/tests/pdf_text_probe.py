# -*- coding: utf-8 -*-
"""pdf_text_probe.py — структурный извлекатель текста из PDF (только stdlib).

Используется тестами фазы 40 (tests/test_round40.py), чтобы программно
подтвердить кириллицу/структуру в РЕАЛЬНО сгенерированном PDF без
дополнительных runtime-зависимостей (pypdf/pymupdf в приложении нет).

Что делает:
  1. разбирает объекты PDF и декодирует потоки (ASCII85Decode + FlateDecode);
  2. читает ToUnicode CMap'ы subset-шрифтов (beginbfchar/beginbfrange);
  3. извлекает текстовые операторы Tj/TJ из content-потоков страниц;
  4. декодирует коды через CMap текущего шрифта в Unicode и склеивает текст.

Ограничение честно зафиксировано: работает с PDF, сгенерированными
ReportLab (наш exporter) — именно этот документ и проверяется.
"""
import base64
import re
import zlib

_STREAM_RE = re.compile(rb"stream\n(.*?)endstream", re.S)
_OBJ_RE = re.compile(rb"(\d+) 0 obj(.*?)endobj", re.S)
_FONT_SWITCH = re.compile(rb"/([A-Za-z]\d+(?:\+\d+)?)\s+[\d.]+\s+Tf")
_LITERAL = re.compile(rb"^\((.*)\)$", re.S)
_HEXSTR = re.compile(rb"^<([0-9a-fA-F\s]+)>$", re.S)

# Лексемы текста: литеральная строка "(...)" либо hex-строка "<...>".
# Строки внутри TJ-массивов попадают в эту же выборку; числовые сдвиги
# массивов на порядок текста не влияют.
_TEXT_TOKEN = re.compile(rb"\((?:[^()\\]|\\.)*\)|<[0-9a-fA-F\s]+>")


def _decode_stream(data: bytes) -> bytes:
    """Декодировать цепочку ASCII85Decode + FlateDecode (или одну из них)."""
    out = data
    for _ in range(6):
        try:
            # ASCII85 (ReportLab пишет с EOD '~>').
            out = base64.a85decode(out, adobe=True)
            continue
        except Exception:
            pass
        try:
            out = zlib.decompress(out)
            continue
        except Exception:
            break
    return out


def _objects(raw: bytes) -> dict:
    """{id: тело объекта}."""
    return {int(m.group(1)): m.group(2) for m in _OBJ_RE.finditer(raw)}


def _stream_of(body: bytes) -> bytes:
    m = _STREAM_RE.search(body)
    return _decode_stream(m.group(1)) if m else b""


def _parse_cmap(stream: bytes) -> dict:
    """ToUnicode CMap -> {code:int: unicode:str}."""
    mapping = {}
    for bf in re.finditer(rb"beginbfchar(.*?)endbfchar", stream, re.S):
        for pair in re.finditer(
                rb"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>", bf.group(1)):
            mapping[int(pair.group(1), 16)] = chr(int(pair.group(2), 16))
    for bf in re.finditer(rb"beginbfrange(.*?)endbfrange", stream, re.S):
        for rng in re.finditer(
                rb"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>",
                bf.group(1)):
            start, end, dst = (int(rng.group(1), 16),
                               int(rng.group(2), 16),
                               int(rng.group(3), 16))
            for i in range(end - start + 1):
                mapping[start + i] = chr(dst + i)
    return mapping


def _unescape_literal(inner: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == 0x5C and i + 1 < len(inner):
            nxt = inner[i + 1]
            mapping = {ord("n"): 0x0A, ord("r"): 0x0D, ord("t"): 0x09,
                       ord("b"): 0x08, ord("f"): 0x0C}
            if nxt in mapping:
                out.append(mapping[nxt])
                i += 2
                continue
            if nxt in (0x28, 0x29, 0x5C):
                out.append(nxt)
                i += 2
                continue
            if 0x30 <= nxt <= 0x37 and i + 3 < len(inner):
                oct_chunk = inner[i + 1:i + 4]
                if all(0x30 <= b <= 0x37 for b in oct_chunk):
                    out.append(int(oct_chunk, 8))
                    i += 4
                    continue
        out.append(ch)
        i += 1
    return bytes(out)


def extract_pdf_pages(pdf_path: str) -> list:
    """Вернуть список текстов PDF постранично (Unicode)."""
    with open(pdf_path, "rb") as f:
        raw = f.read()
    objs = _objects(raw)

    # Шрифты: id -> (basefont, to_unicode_obj_id)
    fonts = {}
    for obj_id, body in objs.items():
        base = re.search(rb"/BaseFont\s*/([^\s/>]+)", body)
        touni = re.search(rb"/ToUnicode\s+(\d+)\s+\d+\s+R", body)
        if base and touni:
            fonts[obj_id] = (base.group(1).decode(), int(touni.group(1)))

    # CMap по имени шрифта.
    cmaps = {}
    for obj_id, body in objs.items():
        stream = _stream_of(body)
        if b"begincmap" not in stream:
            continue
        name = re.search(rb"/CMapName\s*/([^\s>]+)", stream)
        if name:
            cmaps[name.group(1).decode()] = _parse_cmap(stream)

    def _resolve_cmap(font_label, res_fonts):
        font_obj = res_fonts.get(font_label)
        if not font_obj or font_obj not in fonts:
            return {}
        basefont, touni_id = fonts[font_obj]
        # CMap может называться по-другому; пробуем BaseFont и содержимое.
        cmap = cmaps.get(basefont)
        if cmap is None and touni_id in objs:
            stream = _stream_of(objs[touni_id])
            cmap = _parse_cmap(stream)
        return cmap or {}

    def _font_dict_body(font_ref_body):
        """Тело объекта-словаря шрифтов: /Font N 0 R или << /F1 N 0 R … >>."""
        m = re.search(rb"/Font\s+(\d+)\s+\d+\s+R", font_ref_body)
        if m:
            return objs.get(int(m.group(1)), b"")
        m2 = re.search(rb"/Font\s*<<(.*?)>>", font_ref_body, re.S)
        if m2:
            return m2.group(1)
        return font_ref_body

    def _resource_fonts(page_body):
        """/F1 -> obj_id из /Resources страницы (ref или inline)."""
        res_body = b""
        m = re.search(rb"/Resources\s+(\d+)\s+\d+\s+R", page_body)
        if m:
            res_body = objs.get(int(m.group(1)), b"")
        else:
            m2 = re.search(rb"/Resources\s*<<(.*?)>>", page_body, re.S)
            if m2:
                res_body = m2.group(1)
        if not res_body:
            return {}
        fd = _font_dict_body(res_body)
        return {label.decode(): int(obj_id)
                for label, obj_id in re.findall(
                    rb"/(F\d+(?:\+\d+)?)\s+(\d+)\s+\d+\s+R", fd)}

    # Страницы: (obj_id, contents_ids)
    pages = []
    for obj_id, body in objs.items():
        if not re.search(rb"/Type\s*/Page[^s]", body):
            continue
        contents = []
        cm = re.search(rb"/Contents\s+(\d+)\s+\d+\s+R", body)
        if cm:
            contents = [int(cm.group(1))]
        else:
            arr = re.search(rb"/Contents\s*\[(.*?)\]", body, re.S)
            if arr:
                contents = [int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R",
                                                       arr.group(1))]
        pages.append((obj_id, contents))

    pages_text = []
    for _page_id, contents in pages:
        # Шрифты страницы известны только из её /Resources.
        page_body = objs.get(_page_id, b"")
        res_fonts = _resource_fonts(page_body)
        page_parts = []
        for content_id in contents:
            stream = _stream_of(objs.get(content_id, b""))
            if not stream:
                continue
            font_label = None
            cmap = {}
            cursor = 0
            for m in _FONT_SWITCH.finditer(stream):
                # Текст ДО переключения рисовался предыдущим шрифтом.
                _emit_segment(stream[cursor:m.start()], page_parts, cmap)
                font_label = m.group(1).decode()
                cmap = _resolve_cmap(font_label, res_fonts)
                cursor = m.end()
            _emit_segment(stream[cursor:], page_parts, cmap)
        pages_text.append("\n".join(page_parts))
    return pages_text


def extract_pdf_text(pdf_path: str) -> str:
    """Вернуть весь текст PDF (все страницы), декодированный в Unicode."""
    return "\n".join(extract_pdf_pages(pdf_path))


def _emit_segment(segment: bytes, text_parts: list, cmap: dict) -> None:
    """Разобрать кусок контента между переключениями шрифтов."""
    for m in _TEXT_TOKEN.finditer(segment):
        _decode_and_append(m.group(0), text_parts, cmap)


def _decode_and_append(token: bytes, text_parts: list, cmap: dict) -> None:
    if token.startswith(b"<"):
        hm = _HEXSTR.match(token)
        if not hm:
            return
        codes = bytes.fromhex(re.sub(rb"\s", b"", hm.group(1)).decode())
    else:
        lm = _LITERAL.match(token)
        if not lm:
            return
        codes = _unescape_literal(lm.group(1))
    text_parts.append("".join(cmap.get(b, "") for b in codes))
