"""Генератор синтетического PDF с кириллицей — только для стенда W01.

Настоящие сканы в стенд не загружаются. Шрифт с кириллическим покрытием ищется
локально (по умолчанию DejaVu Sans); путь переопределяется CONTROLS_WEB_PDF_FONT.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_NAME = "StandCyrillic"
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
)
MAX_CHARS_PER_LINE = 92
MAX_LINES = 42


def find_font(explicit: str | None = None) -> Path:
    candidates = [Path(explicit)] if explicit else []
    env_font = os.environ.get("CONTROLS_WEB_PDF_FONT")
    if env_font:
        candidates.append(Path(env_font))
    candidates.extend(Path(item) for item in FONT_CANDIDATES)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Не найден TTF-шрифт с кириллицей. Укажите CONTROLS_WEB_PDF_FONT=/путь/к/шрифту.ttf "
        f"(проверены: {', '.join(str(c) for c in candidates)})"
    )


def _register_font(font_path: Path) -> str:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))
    return FONT_NAME


def _wrap(text: str) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if len(candidate) <= MAX_CHARS_PER_LINE:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines[:MAX_LINES]


def build_sample_pdf(
    text: str = "Синтетический документ стенда W01: проверка кириллицы в PDF.",
    *,
    title: str = "Синтетический документ стенда",
    font_path: str | None = None,
) -> tuple[bytes, Path]:
    """Возвращает (байты PDF, путь к использованному шрифту)."""
    used_font = find_font(font_path)
    _register_font(used_font)
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    page.setTitle(title)
    page.setAuthor("Стенд controls-web W01")
    page.setSubject("Синтетические данные, кириллица")
    width, height = A4
    page.setFont(FONT_NAME, 16)
    page.drawString(56, height - 72, title)
    page.setFont(FONT_NAME, 11)
    y = height - 110
    for line in _wrap(text):
        page.drawString(56, y, line)
        y -= 17
    page.setFont(FONT_NAME, 9)
    page.drawString(56, 60, "Документ сгенерирован стендом автоматически и не является рабочим документом.")
    page.showPage()
    page.save()
    return buffer.getvalue(), used_font
