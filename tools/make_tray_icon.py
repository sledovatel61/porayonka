#!/usr/bin/env python3
# tools/make_tray_icon.py
# Иконка приложения для трея (раунд 23) ТОЛЬКО stdlib (zlib+PNG): 64x64 RGBA —
# тёмный круг, акцентное кольцо, «лупа» посередине. Без PIL, чтобы генератор
# работал везде (Pillow используется только pystray на машине пользователя).
#
# Запуск:  python tools/make_tray_icon.py  (пишет porayonka-app/assets/icon.png)

import os
import struct
import sys
import zlib

SIZE = 64


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def render(path: str) -> None:
    cx = cy = (SIZE - 1) / 2.0
    rows = []
    for y in range(SIZE):
        row = bytearray([0])  # filter type 0
        for x in range(SIZE):
            dx, dy = x - cx, y - cy
            d = (dx * dx + dy * dy) ** 0.5
            rgba = (0, 0, 0, 0)                       # прозрачный фон
            if d <= 30.0:                             # внешнее кольцо — акцент
                rgba = (79, 140, 255, 255)            # #4f8cff
            if d <= 26.0:                             # тёмное тело
                rgba = (24, 31, 50, 255)              # #181f32
            # «лупа»: кольцо + ручка
            mx, my = x - (cx - 6), y - (cy - 7)
            md = (mx * mx + my * my) ** 0.5
            if 8.0 <= md <= 12.0:
                rgba = (142, 182, 255, 255)           # светлое стекло лупы
            if 10.5 <= md <= 12.0 and dx < 2 and dy < 2:
                pass
            # ручка лупы — диагональ вниз-вправо
            hx0, hy0, hx1, hy1 = cx + 4, cy + 4, cx + 13, cy + 13
            # расстояние до отрезка
            vx, vy = hx1 - hx0, hy1 - hy0
            t = max(0.0, min(1.0, ((x - hx0) * vx + (y - hy0) * vy) / (vx * vx + vy * vy)))
            px, py = hx0 + vx * t, hy0 + vy * t
            if ((x - px) ** 2 + (y - py) ** 2) <= 3.2 ** 2 and d <= 25.0:
                rgba = (142, 182, 255, 255)
            row += bytes(rgba)
        rows.append(bytes(row))
    raw = b"".join(rows)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw, 9))
           + _chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    print(f"[make_tray_icon] wrote {path} ({len(png)} bytes)")


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "porayonka-app", "assets", "icon.png")
    if len(sys.argv) > 1:
        out = sys.argv[1]
    render(out)
