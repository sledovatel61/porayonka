#!/usr/bin/env python3
# tools/make_pig_sound.py
# Генератор «визжащей свиньи» (аларм срока контроля) ТОЛЬКО stdlib — для раунда 23.
#
# Скачать оригинальный infected_p.wav из дистрибутива Касперского в песочнице
# не получилось (TLS-фильтр рвёт бинарные загрузки), поэтому звук синтезируется
# параметрически: 3 коротких визга с подъёмом тона, «хрипотцой» и grunt-AM.
#
# Подмена: пользователь может просто положить настоящий файл как
#   porayonka-app/assets/pig.wav  (или в %APPDATA%/porayonka/pig.wav)
# — приложение возьмёт его в первую очередь (см. ui/sound_alert.py).
#
# Запуск:  python tools/make_pig_sound.py  (пишет porayonka-app/assets/pig.wav)

import math
import os
import random
import struct
import sys
import wave

SR = 22050          # 16-bit mono — winsound.PlaySound совместим и с Win7


def _squeal(dur, f_lo=950.0, f_hi=2350.0, vib_hz=41.0):
    """Один визг: восходящий глиссандо + сильное вибрато (grunt) + эм -
    огибающая с быстрой атакой; tanh-клиппинг даёт «хрип» вокала."""
    n = int(dur * SR)
    phase = 0.0
    out = []
    # крошечный шумовой «сип» на атаке — делимант свинячьего призвука
    rng = random.Random(7)
    for i in range(n):
        t = i / SR
        x = t / dur
        f = f_lo + (f_hi - f_lo) * (x ** 0.75)
        f *= 1.0 + 0.16 * math.sin(2.0 * math.pi * vib_hz * t)
        phase += 2.0 * math.pi * f / SR
        s = math.sin(phase)
        s = math.tanh(3.2 * s)                      # жёсткое ограничение — «визг»
        # grunt-амплитудная модуляция (поросячьи толчки)
        am = 0.62 + 0.38 * math.sin(2.0 * math.pi * vib_hz * t + 0.6)
        env = min(1.0, x * 14.0) * ((1.0 - x) ** 0.65)
        noise = (rng.random() - 0.5) * max(0.0, 1.0 - x * 9.0)   # шипение атаки
        out.append((s * am + noise * 0.55) * env)
    return out


def render(path: str) -> None:
    samples = []
    samples += _squeal(0.34, 950, 2350, 41)
    samples += [0.0] * int(0.07 * SR)               # короткая пауза
    samples += _squeal(0.30, 1050, 2250, 44)
    samples += [0.0] * int(0.05 * SR)
    samples += _squeal(0.42, 850, 2500, 39)         # финальный — длиннее
    # плавный общий фейд на всём треке, нормализация
    peak = max(1e-9, max(abs(s) for s in samples))
    k = 0.96 / peak
    frames = bytearray()
    for s in samples:
        v = int(max(-1.0, min(1.0, s * k)) * 32767)
        frames += struct.pack("<h", v)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    print(f"[make_pig_sound] wrote {path} ({len(samples)/SR:.2f}s, {os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "porayonka-app", "assets", "pig.wav")
    if len(sys.argv) > 1:
        out = sys.argv[1]
    render(out)
