# core/zonal_distribution_exporter.py
# Фаза 40 — печатная PDF-выгрузка актуального распределения зональных
# криминалистов: заголовок, 3-колоночная решётка карточек, зоны и блок
# «Взаимозаменяемость». Экспортер принимает данные явно и не зависит от
# Flet/Page — его можно тестировать standalone.
import os
import re
import sys
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .zonal_replacement import (
    normalize_zonal_criminalists,
    unique_replacement_pairs,
    format_replacement_pair,
    short_name,
)

_PDF_TITLE = "Зональный принцип распределения отдела криминалистики"
_PDF_SECTION = "Взаимозаменяемость:"
_PDF_EMPTY = "Не указана"
_LETTERS = ("DejaVuSans", "DejaVuSans-Bold")

_FONT_DIR_NAMES = ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "LICENSE")
_KEEP_DOWNLOAD_SUFFIX = ".pdf"


def resource_root() -> str:
    """Корень ресурсов в dev и в frozen (_MEIPASS)."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return str(frozen_root)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def font_path(name: str) -> str:
    """Абсолютный путь к bundled TTF внутри assets/fonts."""
    return os.path.join(resource_root(), "assets", "fonts", name)


def _ensure_fonts() -> None:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    _ = __import__("reportlab")  # явная зависимость для PyInstaller/тестов
    for leaf in _FONT_DIR_NAMES:
        if not os.path.isfile(font_path(leaf)):
            raise RuntimeError(
                "PDF font missing: assets/fonts/%s" % leaf
            )
    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path("DejaVuSans.ttf")))
    pdfmetrics.registerFont(
        TTFont("DejaVuSans-Bold", font_path("DejaVuSans-Bold.ttf"))
    )
    pdfmetrics.registerFontFamily(
        "DejaVuSans",
        normal="DejaVuSans",
        bold="DejaVuSans-Bold",
        italic="DejaVuSans",
        boldItalic="DejaVuSans-Bold",
    )


def safe_download_name(filename: str) -> str:
    """Безопасное имя файла для web-каталога: без path traversal и CJK-мусора."""
    base = os.path.basename(str(filename or ""))
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._-")
    if not base:
        base = "zonal_distribution_unknown"
    if not base.lower().endswith(_KEEP_DOWNLOAD_SUFFIX):
        base += _KEEP_DOWNLOAD_SUFFIX
    return base[:120]


def pdf_filename(now: Optional[datetime] = None) -> str:
    """Имя по умолчанию: zonal_distribution_YYYYMMDD_HHMMSS.pdf."""
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"zonal_distribution_{stamp}.pdf"


class ZonalDistributionPdfExporter:
    """
    Печатная PDF-выгрузка зональных криминалистов.

    Источник истины — переданный ZonalCollection; экспортер НЕ мутирует
    коллекцию и НЕ сохраняет JSON.
    """

    # Размеры страницы (A4, книжная, поля ~20 мм).
    PAGE_WIDTH = 595.27
    PAGE_HEIGHT = 841.89
    LEFT_MARGIN = 44.0
    RIGHT_MARGIN = 44.0
    TOP_MARGIN = 46.0
    BOTTOM_MARGIN = 46.0
    GAP = 16.0

    def export(self, collection, filepath: str) -> None:
        """Сформировать PDF и записать его в filepath (валидный, utf-8)."""
        _ensure_fonts()
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        normalize_zonal_criminalists(collection.criminalists)
        dept_map = self._dept_map()
        cards = self._card_rows(collection, dept_map)
        pairs = unique_replacement_pairs(collection.criminalists)

        usable = self.PAGE_WIDTH - self.LEFT_MARGIN - self.RIGHT_MARGIN
        cell = (usable - 2 * self.GAP) / 3.0

        title_style = ParagraphStyle(
            "title", fontName="DejaVuSans-Bold", fontSize=14, leading=18,
            alignment=TA_CENTER, spaceAfter=8,
        )
        header_style = ParagraphStyle(
            "header", fontName="DejaVuSans-Bold", fontSize=9, leading=11,
            alignment=TA_CENTER, wordWrap="CJK",
        )
        zone_style = ParagraphStyle(
            "zone", fontName="DejaVuSans", fontSize=7.8, leading=9.6,
            alignment=TA_LEFT, wordWrap="CJK", spaceAfter=0,
        )
        pair_style = ParagraphStyle(
            "pair", fontName="DejaVuSans", fontSize=8, leading=11,
            alignment=TA_LEFT, wordWrap="CJK", spaceAfter=3,
        )
        section_style = ParagraphStyle(
            "section", fontName="DejaVuSans-Bold", fontSize=10.5, leading=14,
            alignment=TA_LEFT, spaceBefore=10, spaceAfter=5,
        )

        story = [Paragraph(_PDF_TITLE, title_style)]

        # 3-колоночная решётка. Каждая строка — отдельная Table, поэтому
        # SimpleDocTemplate переносит строку на следующую страницу целиком,
        # а при переполнении просто добавляет страницу.
        for row_cards in cards:
            cells = []
            for card in row_cards:
                cells.append(self._card_table(card, cell, header_style, zone_style))
            for _ in range(3 - len(cells)):
                cells.append(Spacer(1, 1))
            grid = Table(
                [cells],
                colWidths=[cell, cell, cell],
                hAlign="CENTER",
                rowHeights=None,
            )
            grid.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), self.GAP / 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), self.GAP / 2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(grid)

        story.append(Spacer(1, 10))
        story.append(Paragraph(_PDF_SECTION, section_style))
        if pairs:
            for pair in pairs:
                story.append(
                    Paragraph(format_replacement_pair(*pair), pair_style)
                )
        else:
            story.append(Paragraph(_PDF_EMPTY, pair_style))

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=self.LEFT_MARGIN,
            rightMargin=self.RIGHT_MARGIN,
            topMargin=self.TOP_MARGIN,
            bottomMargin=self.BOTTOM_MARGIN,
            title=_PDF_TITLE,
            author="Порайонка",
            subject="Зональный принцип распределения отдела криминалистики",
        )
        doc.build(story)
        self._last_export_path = os.path.abspath(filepath)

    def export_bytes(self, collection) -> bytes:
        """Сформировать PDF в памяти и вернуть байты."""
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".pdf", prefix="zonal_pdf_")
        try:
            os.close(fd)
            self.export(collection, path)
            with open(path, "rb") as f:
                return f.read()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    @staticmethod
    def _dept_map() -> Dict[int, str]:
        from .constants import INITIAL_DEPARTMENTS
        return {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}

    @staticmethod
    def _card_rows(collection, dept_map: Dict[int, str]) -> List[List[dict]]:
        rows = []
        for i in range(0, len(collection.criminalists), 3):
            chunk = collection.criminalists[i:i + 3]
            rows.append([
                {
                    "id": c.id,
                    "full_name": c.full_name,
                    "note": c.note,
                    "department_ids": list(c.zone.department_ids),
                    "dept_map": dept_map,
                }
                for c in chunk
            ])
        return rows

    def _card_table(self, card: dict, cell: float, header_style, zone_style):
        from reportlab.lib import colors
        from reportlab.platypus import Paragraph, Table, TableStyle

        header = Paragraph(
            f"({card['id']}) {card['full_name']}", header_style
        )
        zone_lines = []
        for did in card["department_ids"]:
            name = card["dept_map"].get(did, f"Отдел {did}")
            zone_lines.append(f"- {name}")
        if not zone_lines:
            zone_lines.append("Отделы не закреплены")
        if card["note"]:
            zone_lines.append(f"Примечание: {card['note']}")

        zone = Paragraph("<br/>".join(zone_lines), zone_style)

        table = Table(
            [[header], [zone]],
            colWidths=[cell],
            hAlign="CENTER",
        )
        table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.55, colors.black),
            ("LINEBELOW", (0, 0), (0, 0), 0.55, colors.black),
            ("LINEBELOW", (0, 1), (0, 1), 0, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (0, 0), 5),
            ("BOTTOMPADDING", (0, 0), (0, 0), 4),
            ("TOPPADDING", (0, 1), (0, 1), 4),
            ("BOTTOMPADDING", (0, 1), (0, 1), 6),
        ]))
        return table


# ── Web-helper: безопасная запись под FLET_ASSETS_DIR/downloads ──────────
def web_downloads_dir() -> str:
    base = os.environ.get("FLET_ASSETS_DIR")
    if not base:
        raise RuntimeError("FLET_ASSETS_DIR not set (web-mode only)")
    d = os.path.join(base, "downloads")
    os.makedirs(d, exist_ok=True)
    return d


def web_download_url(filename: str) -> str:
    """URL, под которым Flet раздаёт /assets/downloads/<file>."""
    import urllib.parse
    safe = safe_download_name(filename)
    return "/assets/downloads/" + urllib.parse.quote(safe, safe="/")


def write_web_pdf(filename: str, data: bytes) -> Tuple[str, str]:
    """
    Записать байты PDF только внутрь web-downloads и вернуть
    (абсолютный путь, относительный URL). Path traversal исключён.
    """
    d = web_downloads_dir()
    safe = safe_download_name(filename)
    final = os.path.abspath(os.path.join(d, safe))
    if os.path.dirname(final) != os.path.abspath(d):
        raise RuntimeError("PDF download path escaped downloads dir")
    with open(final, "wb") as f:
        f.write(data)
    return final, web_download_url(safe)
