# core/zonal_distribution_exporter.py
# Фаза 40: печатная PDF-выгрузка распределения зональных криминалистов.
#
# Отдельный exporter: принимает данные ЯВНО (список Criminalist в текущем
# порядке + карту id отдела -> название) и НЕ мутирует коллекцию и не
# сохраняет JSON. Рисование полностью в ReportLab, без Flet/Page — модуль
# тестируется standalone.
#
# Формат повторяет структуру эталона docs/reference/zonal_export_reference.pdf:
#   * A4 portrait, белый фон/чёрный текст, печатные поля;
#   * заголовок «Зональный принцип распределения отдела криминалистики»
#     (повторяется коротким на каждой странице многостраничной выгрузки);
#   * карточки в текущем сохранённом порядке, три в ряд, тонкая чёрная
#     рамка и горизонтальное разделение шапки и зоны;
#   * шапка: «(N) ФИО» жирно по центру, переносится без обрезания;
#   * закреплённые отделы — отдельными строками с маркером «-»;
#   * примечание — отдельной компактной строкой «Примечание: …»
#     (не смешивается с названиями отделов);
#   * пустая зона → «Отделы не закреплены» (человек не пропадает);
#   * ниже сетки — заголовок «Взаимозаменяемость:» и уникальные пары
#     «Иванов И.И. (1) ↔ Петров П.П. (2)», либо «Не указана»;
#   * 16+ человек и длинные тексты — корректная многостраничная выгрузка
#     без потери записей и без наложения текста;
#   * кириллица и «↔» — реальными glyph через встроенный (bundled) TTF.
#
# PDF-библиотека: reportlab==4.4.10 (зафиксирована в requirements*.txt и
# requirements-win7-web.txt). Шрифты: DejaVu Sans 2.37 (regular/bold),
# лицензия Bitstream Vera — в assets/fonts/ (входят во все сборки через
# datas=("assets", "assets") в четырёх .spec).

import os
import sys
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

from .zonal_replacement import unique_pairs, short_full_name

# ────────────────────────────────────────────────────────────────
# КОНСТАНТЫ РАСКЛАДКИ (pt; 1 pt = 1/72", A4 = 595.28 x 841.89)
# ────────────────────────────────────────────────────────────────
_PAGE_W, _PAGE_H = A4
_MARGIN_L = 40.0
_MARGIN_R = 40.0
_MARGIN_TOP = 46.0
_MARGIN_BOTTOM = 46.0

_TITLE = "Зональный принцип распределения отдела криминалистики"
_TITLE_SIZE = 13.5            # ровно вписывается между печатными полями
_TITLE_BOTTOM_GAP = 10.0      # зазор после заголовка до сетки

_REPL_HEADING = "Взаимозаменяемость:"
_REPL_HEADING_SIZE = 11.5
_REPL_LINE_SIZE = 9.5
_REPL_LEAD = 12.2
_REPL_TOP_GAP = 12.0          # отступ блока пар от последней карточки
_NO_PAIRS = "Не указана"

# ── Компактная геометрия карточек ─────────────────────────────────────────
# Метрики подобраны так, чтобы ШТАТНЫЙ набор (16 человек в 6 рядах по 3 +
# блок «Взаимозаменяемость» с парами) гарантированно умещался на ОДНУ
# страницу A4 portrait (бюджет ≈ 705 pt между заголовком и нижним полем).
# Проверено измерениями: дефолтные 16 + 8 пар и 16 человек с 4 длинными
# отделами каждый → 1 страница; читаемость сохранена (шапка 9.2 pt).
# Нештатно большие наборы не теряют данные и занимают несколько страниц.
_CARD_GAP_X = 12.0
_CARD_GAP_Y = 8.0
_CARD_PAD = 4.0
_HEADER_SIZE = 9.2
_HEADER_LEAD = 11.6
_DEPT_SIZE = 8.6
_DEPT_LEAD = 10.8
_NOTE_SIZE = 7.8
_NOTE_LEAD = 9.8
_BODY_ITEM_GAP = 2.4
_SEP_BELOW_HEADER = 1.8       # зазор между шапкой и линией-разделителем
_BODY_ABOVE_SEP = 2.0         # зазор между линией-разделителем и телом
_LINE_W = 0.9

_FONT_REG = "PorayonkaDejaVuSans"
_FONT_BOLD = "PorayonkaDejaVuSans-Bold"
_FONT_FILE_REG = "DejaVuSans.ttf"
_FONT_FILE_BOLD = "DejaVuSans-Bold.ttf"
_FONT_DIR = "fonts"


class ZonalPdfError(Exception):
    """Понятная ошибка формирования PDF (текст ASCII-safe)."""


# ────────────────────────────────────────────────────────────────
# ШРИФТЫ: bundled TTF (dev и frozen/_MEIPASS), без C:\Windows\Fonts
# ────────────────────────────────────────────────────────────────
def fonts_dir() -> str:
    """Каталог bundled-шрифтов: работает в dev и в frozen (_MEIPASS)."""
    override = os.environ.get("PORAYONKA_FONT_DIR")
    if override:
        return override
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
        return os.path.join(base, "assets", _FONT_DIR)
    # core/zonal_distribution_exporter.py -> porayonka-app/assets/fonts
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(app_dir, "assets", _FONT_DIR)


def _font_path(file_name: str) -> str:
    path = os.path.join(fonts_dir(), file_name)
    if not os.path.isfile(path):
        raise ZonalPdfError(
            "PDF font not found: %s (expected bundled in %s)" % (file_name, path))
    return path


def _register_fonts() -> None:
    try:
        pdfmetrics.registerFont(TTFont(_FONT_REG, _font_path(_FONT_FILE_REG)))
        pdfmetrics.registerFont(TTFont(_FONT_BOLD, _font_path(_FONT_FILE_BOLD)))
    except ZonalPdfError:
        raise
    except Exception as ex:  # повреждённый TTF и т.п.
        raise ZonalPdfError("Cannot load bundled PDF fonts: %s" % (ex,))


_register_fonts()


# ────────────────────────────────────────────────────────────────
# ЧИСТЫЕ ХЕЛПЕРЫ ТЕКСТА/РАСКЛАДКИ
# ────────────────────────────────────────────────────────────────
def _text_width(text: str, font: str, size: float) -> float:
    try:
        return pdfmetrics.stringWidth(text, font, size)
    except Exception:
        return len(text) * size * 0.55


def _wrap_line(text: str, font: str, size: float, max_width: float) -> List[str]:
    """Жадный перенос по словам; сверхдлинное слово режется посимвольно.

    Символы не теряются: перенос только перераспределяет текст по строкам
    (пробел на границе строк не сохраняется — строка закрывается ДО слова).
    """
    lines: List[str] = []
    current = ""
    for word in text.split(" "):
        candidate = word if not current else current + " " + word
        if _text_width(candidate, font, size) <= max_width:
            current = candidate
            continue
        # Слово не влезает в текущую строку — строка закрывается.
        if current:
            lines.append(current)
            current = ""
        # Слово само шире строки (в т.ч. ПЕРВОЕ в тексте) — посимвольная
        # нарезка; остаток остаётся «текущей» строкой для следующих слов.
        while word and _text_width(word, font, size) > max_width:
            cut = 1
            while (cut < len(word)
                   and _text_width(word[:cut], font, size) <= max_width):
                cut += 1
            lines.append(word[:cut])
            word = word[cut:]
        if word:
            current = word
    if current:
        lines.append(current)
    return lines


def _card_inner_width() -> float:
    usable = _PAGE_W - _MARGIN_L - _MARGIN_R
    return (usable - _CARD_GAP_X * 2) / 3.0 - _CARD_PAD * 2


def _card_width() -> float:
    usable = _PAGE_W - _MARGIN_L - _MARGIN_R
    return (usable - _CARD_GAP_X * 2) / 3.0


def _header_lines(criminalist) -> List[str]:
    """Строки шапки: «(N) ФИО», перенос внутри карточки."""
    text = f"({criminalist.id}) {(criminalist.full_name or '').strip()}"
    return _wrap_line(text, _FONT_BOLD, _HEADER_SIZE, _card_inner_width())


def _card_body_blocks(criminalist, dept_map: dict) -> List[dict]:
    """Блоки тела карточки (зона + примечание) с готовыми строками.

    kind='dept' — строка с маркером «- » (отдел или «Отделы не закреплены»);
    kind='note' — компактная строка «Примечание: …» (отдельно от отделов).
    """
    width = _card_inner_width()
    blocks: List[dict] = []
    zone = getattr(criminalist, "zone", None)
    dept_ids = list(getattr(zone, "department_ids", None) or [])
    if dept_ids:
        marker = "- "
        marker_w = _text_width(marker, _FONT_REG, _DEPT_SIZE)
        for department_id in dept_ids:
            name = dept_map.get(department_id, f"Отдел {department_id}")
            # Первая строка рисуется как «маркер + название», продолжения —
            # с висячим отступом под маркер.
            lines = _wrap_line(name, _FONT_REG, _DEPT_SIZE,
                               max(20.0, width - marker_w))
            blocks.append({
                "kind": "dept", "size": _DEPT_SIZE, "lead": _DEPT_LEAD,
                "lines": lines, "indent_first": marker, "indent_w": marker_w,
                "hanging": True,
            })
    else:
        blocks.append({
            "kind": "dept", "size": _DEPT_SIZE, "lead": _DEPT_LEAD,
            "lines": ["Отделы не закреплены"], "indent_first": "",
            "indent_w": 0.0, "hanging": False,
        })
    note = (criminalist.note or "").strip()
    if note:
        prefix = "Примечание: "
        prefix_w = _text_width(prefix, _FONT_BOLD, _NOTE_SIZE)
        lines = _wrap_line(note, _FONT_REG, _NOTE_SIZE,
                           max(20.0, width - prefix_w))
        blocks.append({
            "kind": "note", "size": _NOTE_SIZE, "lead": _NOTE_LEAD,
            "lines": lines, "indent_first": prefix, "indent_w": prefix_w,
            "hanging": True, "prefix_bold": True,
        })
    return blocks


# ────────────────────────────────────────────────────────────────
# ЭКСПОРТЁР
# ────────────────────────────────────────────────────────────────
class ZonalDistributionPdfExporter:
    """Формирование PDF распределения зональных (структура эталона)."""

    def export(self, criminalists: List, dept_map: dict,
               filepath: str) -> int:
        """Сохранить PDF в filepath; возвращает число страниц.

        criminalists — список Criminalist В ТЕКУЩЕМ сохранённом порядке
        (никто не отбрасывается: ни is_active=False, ни пустая зона);
        dept_map — {id отдела: название} (только расшифровка ID отделов).
        """
        try:
            return self._build(criminalists or [], dept_map or {}, filepath)
        except ZonalPdfError:
            raise
        except Exception as ex:
            raise ZonalPdfError("PDF build failed: %s" % (ex,))

    # ── Построение ─────────────────────────────────────────────────
    def _build(self, criminalists: List, dept_map: dict,
               filepath: str) -> int:
        c = rl_canvas.Canvas(filepath, pagesize=A4, pageCompression=1)
        c.setTitle(_TITLE)
        c.setAuthor("Porayonka")
        try:
            c.setSubject("Zonal criminalists distribution")
        except Exception:
            pass
        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0, 0, 0)

        def start_page() -> float:
            """Нарисовать заголовок на ТЕКУЩЕЙ странице; вернуть верх контента."""
            c.setFillColorRGB(0, 0, 0)
            c.setStrokeColorRGB(0, 0, 0)
            c.setFont(_FONT_BOLD, _TITLE_SIZE)
            # Заголовок целиком внутри печатных полей (верх глифов ≤ margin).
            baseline = _PAGE_H - _MARGIN_TOP - _TITLE_SIZE
            c.drawCentredString(_PAGE_W / 2.0, baseline, _TITLE)
            return baseline - _TITLE_SIZE * 1.6 - _TITLE_BOTTOM_GAP

        def new_page() -> float:
            """Закончить текущую страницу и начать следующую с заголовком."""
            c.showPage()
            return start_page()

        content_top = start_page()
        y = content_top
        rows = [criminalists[i:i + 3]
                for i in range(0, len(criminalists), 3)]
        pairs = unique_pairs(criminalists)
        max_w = _PAGE_W - _MARGIN_L - _MARGIN_R

        # ── Подготовка рядов и нижнего блока ДО отрисовки ───────────
        # Фаза 40 (дополнение, п.5.1): блок «Взаимозаменяемость» измеряется
        # и РЕЗЕРВИРУЕТСЯ до раскладки карточек. Если штатный набор (все
        # ряды + отступ + заголовок + строки пар) умещается между заголовком
        # документа и нижним полем — вывод гарантированно одна страница A4;
        # карточки в этом режиме никогда не занимают зарезервированный низ.
        # Нештатно большие наборы идут прежним многостраничным потоком: без
        # потери записей, заголовок документа повторяется на каждой странице.
        prepared_rows = []
        grid_h = 0.0
        for row in rows:
            prepared = []
            for crim in row:
                header = _header_lines(crim)
                header_h = len(header) * _HEADER_LEAD
                body = _card_body_blocks(crim, dept_map)
                body_h = sum(len(b["lines"]) * b["lead"]
                             for b in body)
                body_h += max(0, len(body) - 1) * _BODY_ITEM_GAP
                card_h = (_CARD_PAD * 2 + header_h + _SEP_BELOW_HEADER
                          + _LINE_W + _BODY_ABOVE_SEP + body_h)
                prepared.append({
                    "crim": crim, "header": header, "header_h": header_h,
                    "body": body, "body_h": body_h, "card_h": card_h,
                })
            row_h = max(p["card_h"] for p in prepared)
            prepared_rows.append((prepared, row_h))
            grid_h += row_h
        if prepared_rows:
            grid_h += _CARD_GAP_Y * (len(prepared_rows) - 1)

        pairs_h = self._pairs_block_height(pairs)
        # Одна страница: после последнего ряда (с учётом хвостового зазора)
        # остаётся место под _REPL_TOP_GAP + весь блок пар до нижнего поля.
        fits_one_page = bool(prepared_rows) and (
            content_top - grid_h - _CARD_GAP_Y - _REPL_TOP_GAP - pairs_h
            >= _MARGIN_BOTTOM - 0.05
        )

        # ── Сетка карточек: три в ряд, ряды одной высоты ────────────
        for prepared, row_h in prepared_rows:
            # Ряд не помещается, а страница уже не пустая — новая страница
            # (в режиме fits_one_page ряды не могут упереться в низ: место
            # под блок пар зарезервировано ДО раскладки карточек).
            if (not fits_one_page and y - row_h < _MARGIN_BOTTOM
                    and y < content_top):
                content_top = new_page()
                y = content_top

            for idx, p in enumerate(prepared):
                x0 = _MARGIN_L + idx * (_card_width() + _CARD_GAP_X)
                self._draw_card(c, x0, y, row_h, p, dept_map)
            y -= row_h + _CARD_GAP_Y

        # ── Блок взаимозаменяемости ─────────────────────────────────
        block_top = y - _REPL_TOP_GAP
        heading_needs = _REPL_HEADING_SIZE * 1.9 + 4
        if (not fits_one_page
                and block_top - heading_needs < _MARGIN_BOTTOM
                and y < content_top):
            content_top = new_page()
            y = content_top
            block_top = y - _REPL_TOP_GAP
        y = block_top

        heading_done = False

        def draw_heading() -> None:
            nonlocal y, heading_done
            if heading_done:
                return
            c.setFont(_FONT_BOLD, _REPL_HEADING_SIZE)
            c.drawString(_MARGIN_L, y - _REPL_HEADING_SIZE * 0.8,
                         _REPL_HEADING)
            y -= _REPL_HEADING_SIZE * 1.7
            heading_done = True

        if not pairs:
            draw_heading()
            c.setFont(_FONT_REG, _REPL_LINE_SIZE)
            c.drawString(_MARGIN_L, y - _REPL_LINE_SIZE * 0.8, _NO_PAIRS)
        else:
            for a, b in pairs:
                text = (f"{short_full_name(a.full_name)} ({a.id}) "
                        f"\u2194 {short_full_name(b.full_name)} ({b.id})")
                lines = _wrap_line(text, _FONT_REG, _REPL_LINE_SIZE, max_w)
                block_h = len(lines) * _REPL_LEAD + 1.0
                if (not fits_one_page and y - block_h < _MARGIN_BOTTOM):
                    content_top = new_page()
                    y = content_top
                    heading_done = False
                draw_heading()
                for line in lines:
                    c.setFont(_FONT_REG, _REPL_LINE_SIZE)
                    c.drawString(_MARGIN_L, y - _REPL_LINE_SIZE * 0.8, line)
                    y -= _REPL_LEAD
                y -= 1.0

        pages = c.getPageNumber()
        c.save()
        return pages

    def _pairs_block_height(self, pairs) -> float:
        """Высота блока «Взаимозаменяемость» от его верха (по модели отрисовки).

        Заголовок занимает 1.7*size, каждая строка пары — lead с зазором 1 pt
        после пары; перенос строк — тем же _wrap_line/шириной, что и при
        отрисовке, поэтому оценка совпадает с реальным расходом места.
        """
        if not pairs:
            return _REPL_HEADING_SIZE * 1.9 + 4
        h = _REPL_HEADING_SIZE * 1.7
        max_w = _PAGE_W - _MARGIN_L - _MARGIN_R
        for a, b in pairs:
            text = (f"{short_full_name(a.full_name)} ({a.id}) "
                    f"\u2194 {short_full_name(b.full_name)} ({b.id})")
            lines = _wrap_line(text, _FONT_REG, _REPL_LINE_SIZE, max_w)
            h += len(lines) * _REPL_LEAD + 1.0
        return h

    def _draw_card(self, c, x0: float, y_top: float, row_h: float,
                   p: dict, dept_map: dict) -> None:
        """Отрисовать карточку высотой row_h (единой на ряд).

        Модель «боксов»: каждая текстовая строка занимает бокс высотой lead,
        базовая линия — на 0.8*size ниже верха бокса. Размеры, посчитанные в
        _build (card_h), в точности соответствуют отрисовке, поэтому текст
        никогда не выходит за рамку.
        """
        width = _card_width()
        y_bottom = y_top - row_h
        c.setLineWidth(_LINE_W)
        c.rect(x0, y_bottom, width, row_h, stroke=1, fill=0)

        # Шапка «(N) ФИО» — по центру карточки.
        box_top = y_top - _CARD_PAD
        for line in p["header"]:
            c.setFont(_FONT_BOLD, _HEADER_SIZE)
            c.drawCentredString(x0 + width / 2.0,
                                box_top - _HEADER_SIZE * 0.8, line)
            box_top -= _HEADER_LEAD

        # Горизонтальный разделитель шапки и зоны.
        sep_y = box_top - _SEP_BELOW_HEADER
        c.setLineWidth(_LINE_W)
        c.line(x0 + _CARD_PAD, sep_y, x0 + width - _CARD_PAD, sep_y)

        # Тело: отделы с маркером «- », затем отдельно примечание.
        box_top = sep_y - _LINE_W - _BODY_ABOVE_SEP
        first = True
        for block in p["body"]:
            if not first:
                box_top -= _BODY_ITEM_GAP
            first = False
            for i, line in enumerate(block["lines"]):
                baseline = box_top - block["size"] * 0.8
                x_text = x0 + _CARD_PAD
                if i == 0:
                    prefix = block.get("indent_first") or ""
                    if prefix:
                        c.setFont(_FONT_BOLD if block.get("prefix_bold")
                                  else _FONT_REG, block["size"])
                        c.drawString(x_text, baseline, prefix)
                        x_text += block.get("indent_w", 0.0)
                    if line:
                        c.setFont(_FONT_REG, block["size"])
                        c.drawString(x_text, baseline, line)
                else:
                    if block.get("hanging"):
                        x_text += block.get("indent_w", 0.0)
                    c.setFont(_FONT_REG, block["size"])
                    c.drawString(x_text, baseline, line)
                box_top -= block["lead"]


# ────────────────────────────────────────────────────────────────
# WEB-ПОМОЩНИК (чистый, без Flet): безопасная отдача PDF браузеру
# ────────────────────────────────────────────────────────────────
def get_web_downloads_dir() -> str:
    """Каталог downloads внутри FLET_ASSETS_DIR (web-режим).

    Именно этот каталог сервер Flet раздаёт как /assets/downloads/.
    Desktop-режим этот helper не использует (там FilePicker.save_file).
    """
    base = os.environ.get("FLET_ASSETS_DIR") or ""
    if not base:
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        base = os.path.join(appdata, "porayonka", "web_assets")
    d = os.path.join(base, "downloads")
    os.makedirs(d, exist_ok=True)
    return d


def sanitize_pdf_filename(name: str,
                          fallback: str = "zonal_distribution.pdf") -> str:
    """Безопасное имя файла: только имя, без путей/разделителей/метасимволов."""
    name = (name or "").replace("\\", "/").split("/")[-1].strip()
    name = "".join(ch for ch in name if ch not in '<>:"|?*')
    if not name or name in (".", "..") or not name.lower().endswith(".pdf"):
        return fallback
    return name


def reserve_unique_pdf_path(downloads_dir: str, name: str) -> str:
    """Атомарно зарезервировать уникальный путь внутри downloads_dir.

    Имя очищается (без path traversal); при коллизии добавляется суффикс
    _1, _2… Резервация через O_CREAT|O_EXCL исключает выбор одного имени
    двумя одновременными экспортами.
    """
    d = os.path.abspath(downloads_dir)
    os.makedirs(d, exist_ok=True)
    base_name = sanitize_pdf_filename(name)
    stem, dot, suffix = base_name.rpartition(".")
    candidate = os.path.join(d, base_name)
    i = 1
    while True:
        try:
            fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.close(fd)
            return candidate
        except FileExistsError:
            candidate = os.path.join(
                d, f"{stem}_{i}{dot}{suffix}" if dot else f"{base_name}_{i}")
            i += 1
        except OSError:
            raise ZonalPdfError(
                "Cannot write PDF download dir: %s" % (d,))


def asset_download_url(file_name: str) -> str:
    """URL /assets/downloads/<file> с безопасным квотированием имени."""
    from urllib.parse import quote
    safe = sanitize_pdf_filename(file_name)
    return "/assets/downloads/" + quote(safe, safe="")


def export_pdf_for_web(criminalists: List, dept_map: dict,
                       downloads_dir: Optional[str] = None,
                       file_name: Optional[str] = None,
                       timestamp: Optional[str] = None) -> dict:
    """Сформировать PDF в web-downloads; вернуть {path, filename, url}.

    Один вызов: экспорт + уникальное безопасное имя + контроль каталога.
    Используется zonal_tab в web-режиме; Flet здесь не участвует.
    """
    if downloads_dir is None:
        downloads_dir = get_web_downloads_dir()
    if file_name is None:
        if not timestamp:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"zonal_distribution_{timestamp}.pdf"
    path = reserve_unique_pdf_path(downloads_dir, file_name)
    tmp = path + ".tmp"
    try:
        ZonalDistributionPdfExporter().export(criminalists, dept_map, tmp)
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise
    # Контроль: итоговый файл строго внутри разрешённого каталога.
    if os.path.dirname(os.path.abspath(path)) != os.path.abspath(downloads_dir):
        raise ZonalPdfError("PDF path escaped downloads dir")
    return {
        "path": path,
        "filename": os.path.basename(path),
        "url": asset_download_url(os.path.basename(path)),
    }
