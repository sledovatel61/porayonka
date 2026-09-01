"""Generate the Porayonka installer artwork.

Creates the edition icon family plus the standard Inno Setup wizard images.
The script intentionally lives outside the application code.  It only needs
Pillow, which the Windows distributive build scripts already install.

Run from any directory:
    python porayonka-app/installer/images/generate_icons.py
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SIZE = 1024
ICO_SIZES = ((16, 16), (24, 24), (32, 32), (48, 48),
             (64, 64), (96, 96), (128, 128), (256, 256))
RESAMPLE = Image.Resampling.LANCZOS

# Product palette (AGENTS.md, dark theme) with a slightly brighter icon accent.
NAVY_950 = (2, 6, 23)
NAVY_900 = (7, 13, 34)
NAVY_800 = (15, 28, 58)
BLUE = (59, 130, 246)
BLUE_LIGHT = (102, 166, 255)
CYAN = (34, 211, 238)
VIOLET = (139, 92, 246)
TEAL = (16, 185, 129)
AMBER = (245, 158, 11)
WHITE = (248, 250, 252)


def _rounded_mask(size: int, box: tuple[int, int, int, int], radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
    return mask


def _linear_gradient(
    size: tuple[int, int],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    *,
    horizontal: bool = False,
) -> Image.Image:
    width, height = size
    gradient = Image.new("RGBA", size)
    pixels = gradient.load()
    denominator = max(1, (width if horizontal else height) - 1)
    for pos in range(width if horizontal else height):
        t = pos / denominator
        color = tuple(round(start[i] * (1 - t) + end[i] * t) for i in range(3)) + (255,)
        if horizontal:
            for y in range(height):
                pixels[pos, y] = color
        else:
            for x in range(width):
                pixels[x, pos] = color
    return gradient


def _radial_glow(
    size: tuple[int, int],
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    opacity: int,
) -> Image.Image:
    width, height = size
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    px = glow.load()
    left = max(0, center[0] - radius)
    right = min(width, center[0] + radius)
    top = max(0, center[1] - radius)
    bottom = min(height, center[1] + radius)
    for y in range(top, bottom):
        for x in range(left, right):
            dist = math.hypot(x - center[0], y - center[1]) / radius
            if dist < 1:
                alpha = round(opacity * (1 - dist) ** 2)
                px[x, y] = (*color, alpha)
    return glow


def _composite_color_through_mask(
    image: Image.Image,
    color_layer: Image.Image,
    mask: Image.Image,
) -> None:
    clipped = Image.new("RGBA", image.size, (0, 0, 0, 0))
    clipped.paste(color_layer, (0, 0), mask)
    image.alpha_composite(clipped)


def _tile_background() -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    tile_box = (72, 60, 952, 940)
    tile_mask = _rounded_mask(SIZE, tile_box, 218)

    # Soft detached shadow, still legible on both light and dark desktops.
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((80, 82, 944, 962), radius=210, fill=(0, 0, 0, 178))
    shadow = shadow.filter(ImageFilter.GaussianBlur(38))
    image.alpha_composite(shadow)

    tile = _linear_gradient((SIZE, SIZE), NAVY_800, NAVY_950)
    tile.alpha_composite(_radial_glow((SIZE, SIZE), (760, 220), 520, BLUE, 100))
    tile.alpha_composite(_radial_glow((SIZE, SIZE), (245, 785), 440, VIOLET, 42))
    _composite_color_through_mask(image, tile, tile_mask)

    # Fine rim and inset highlight make the silhouette survive small sizes.
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(tile_box, radius=218, outline=(91, 144, 255, 155), width=9)
    draw.rounded_rectangle((88, 76, 936, 924), radius=202, outline=(255, 255, 255, 25), width=4)

    # Very restrained cartographic grid inside the tile.
    grid = Image.new("RGBA", image.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid, "RGBA")
    for x in range(178, 900, 112):
        gd.line((x, 126, x - 86, 890), fill=(111, 177, 255, 18), width=3)
    for y in range(170, 880, 112):
        gd.line((122, y, 906, y + 56), fill=(111, 177, 255, 16), width=3)
    grid.putalpha(Image.composite(grid.getchannel("A"), Image.new("L", image.size, 0), tile_mask))
    image.alpha_composite(grid)
    return image


def _draw_main_mark(image: Image.Image) -> None:
    # The mark retains the lens + diagonal handle from assets/icon.png.
    mark_mask = Image.new("L", image.size, 0)
    md = ImageDraw.Draw(mark_mask)
    lens_box = (214, 188, 663, 637)
    md.ellipse(lens_box, outline=255, width=66)
    md.line((609, 583, 782, 756), fill=255, width=91)
    md.ellipse((564, 538, 654, 628), fill=255)
    md.ellipse((735, 709, 826, 800), fill=255)

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_mask = mark_mask.filter(ImageFilter.GaussianBlur(30))
    glow.paste((*BLUE, 122), (0, 0, SIZE, SIZE), glow_mask)
    image.alpha_composite(glow)

    mark_gradient = _linear_gradient((SIZE, SIZE), CYAN, BLUE, horizontal=False)
    _composite_color_through_mask(image, mark_gradient, mark_mask)

    # Inner bevel/highlight.
    draw = ImageDraw.Draw(image, "RGBA")
    draw.arc((226, 200, 651, 625), 202, 340, fill=(220, 243, 255, 210), width=10)
    draw.line((614, 584, 776, 746), fill=(190, 226, 255, 120), width=10)

    # Three districts/nodes in the lens. They merge into a clear dot at 16 px.
    node_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    nd = ImageDraw.Draw(node_layer, "RGBA")
    nd.line((330, 428, 420, 345, 512, 443), fill=(132, 190, 255, 145), width=14, joint="curve")
    for x, y, r, color in (
        (330, 428, 25, CYAN),
        (420, 345, 21, BLUE_LIGHT),
        (512, 443, 25, AMBER),
    ):
        nd.ellipse((x-r, y-r, x+r, y+r), fill=(*color, 255), outline=(255, 255, 255, 190), width=6)
    image.alpha_composite(node_layer)


def _badge_base(image: Image.Image, accent: tuple[int, int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    badge = Image.new("RGBA", image.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge, "RGBA")

    # Shadow and outer halo.
    halo = Image.new("RGBA", image.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse((644, 627, 934, 917), fill=(*accent, 120))
    halo = halo.filter(ImageFilter.GaussianBlur(28))
    image.alpha_composite(halo)

    bd.ellipse((651, 634, 927, 910), fill=(5, 12, 30, 250), outline=(*accent, 255), width=16)
    bd.ellipse((671, 654, 907, 890), fill=(*accent, 224), outline=(255, 255, 255, 95), width=5)
    return badge, bd


def _draw_admin_badge(image: Image.Image) -> None:
    badge, draw = _badge_base(image, VIOLET)
    # Shield + keyhole: clear and dignified without using any official crest.
    shield = [(789, 690), (858, 717), (850, 800), (789, 855), (728, 800), (720, 717)]
    draw.polygon(shield, fill=(24, 22, 64, 205), outline=WHITE + (255,), width=10)
    draw.ellipse((771, 748, 807, 784), fill=WHITE + (255,))
    draw.rounded_rectangle((781, 772, 797, 817), radius=8, fill=WHITE + (255,))
    image.alpha_composite(badge)


def _draw_user_badge(image: Image.Image) -> None:
    badge, draw = _badge_base(image, TEAL)
    # Neutral human profile mark.
    draw.ellipse((755, 699, 825, 769), fill=WHITE + (255,))
    draw.rounded_rectangle((718, 782, 862, 844), radius=31, fill=WHITE + (255,))
    draw.ellipse((736, 744, 844, 824), fill=WHITE + (255,))
    image.alpha_composite(badge)


def _draw_web_badge(image: Image.Image) -> None:
    badge, draw = _badge_base(image, CYAN)
    # Globe remains recognizable down to 16 px.
    globe = (714, 697, 866, 849)
    draw.ellipse(globe, outline=WHITE + (255,), width=11)
    draw.arc((746, 697, 834, 849), 84, 276, fill=WHITE + (255,), width=9)
    draw.arc((746, 697, 834, 849), 264, 96, fill=WHITE + (255,), width=9)
    draw.line((716, 773, 864, 773), fill=WHITE + (255,), width=9)
    draw.arc((722, 719, 858, 809), 192, 348, fill=WHITE + (235,), width=7)
    draw.arc((722, 737, 858, 831), 12, 168, fill=WHITE + (235,), width=7)
    image.alpha_composite(badge)


def _draw_admin_web_badge(image: Image.Image) -> None:
    """Раунд 37 (задача 3): значок АДМИНСКОЙ web-редакции для Win7 —
    фиолетовый щит админа справа + бирюзовый глобус web ЗЕРКАЛЬНО слева,
    чтобы все четыре установщика различались с первого взгляда."""
    _draw_admin_badge(image)
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    _draw_web_badge(layer)
    image.alpha_composite(layer.transpose(Image.Transpose.FLIP_LEFT_RIGHT))


def build_icon(badge: str | None = None) -> Image.Image:
    image = _tile_background()
    _draw_main_mark(image)
    if badge == "admin":
        _draw_admin_badge(image)
    elif badge == "user":
        _draw_user_badge(image)
    elif badge == "web":
        _draw_web_badge(image)
    elif badge == "admin_web":
        _draw_admin_web_badge(image)
    return image


def _save_ico(image: Image.Image, path: Path) -> None:
    image.save(path, format="ICO", sizes=ICO_SIZES, bitmap_format="png")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: Iterable[Path] = (
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _centered_text(
    draw: ImageDraw.ImageDraw,
    canvas_width: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((canvas_width - (box[2] - box[0])) // 2, y), text, font=font, fill=fill)


def _make_wizard_image(icon: Image.Image) -> Image.Image:
    """Build the classic 164×314 Inno Setup side panel at 4× quality."""
    scale = 4
    width, height = 164 * scale, 314 * scale
    panel = _linear_gradient((width, height), NAVY_800, NAVY_950)
    panel.alpha_composite(_radial_glow(panel.size, (126 * scale, 68 * scale),
                                       145 * scale, BLUE, 105))
    panel.alpha_composite(_radial_glow(panel.size, (26 * scale, 268 * scale),
                                       115 * scale, VIOLET, 65))
    draw = ImageDraw.Draw(panel, "RGBA")

    # Quiet map/grid texture connects the artwork to the district-search UI.
    for x in range(-88, 230, 31):
        draw.line((x * scale, 0, (x + 122) * scale, height),
                  fill=(124, 181, 255, 18), width=scale)
    for y in range(14, 314, 32):
        draw.line((0, y * scale, width, (y + 28) * scale),
                  fill=(124, 181, 255, 15), width=scale)
    draw.line((14 * scale, 24 * scale, 14 * scale, 290 * scale),
              fill=(*CYAN, 72), width=scale)

    # Use the same master mark as the executable icons, not a separate logo.
    mark_side = 112 * scale
    mark = icon.resize((mark_side, mark_side), RESAMPLE)
    panel.alpha_composite(mark, ((width - mark_side) // 2, 25 * scale))

    _centered_text(draw, width, 151 * scale, "Порайонка",
                   _font(15 * scale, True), WHITE + (255,))
    _centered_text(draw, width, 174 * scale, "2.0  •  DARK FINAL",
                   _font(7 * scale, True), (148, 201, 255, 245))

    # A small route with glowing district nodes balances the lower panel.
    route = [(31, 250), (68, 222), (103, 247), (136, 215)]
    route_scaled = [(x * scale, y * scale) for x, y in route]
    glow = Image.new("RGBA", panel.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, "RGBA")
    gd.line(route_scaled, fill=(*BLUE, 110), width=5 * scale, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(6 * scale))
    panel.alpha_composite(glow)
    draw.line(route_scaled, fill=(102, 166, 255, 185), width=2 * scale, joint="curve")
    for index, (x, y) in enumerate(route):
        radius = 5 if index in (0, len(route) - 1) else 4
        color = AMBER if index == len(route) - 1 else CYAN
        draw.ellipse(((x - radius) * scale, (y - radius) * scale,
                      (x + radius) * scale, (y + radius) * scale),
                     fill=(*color, 255), outline=WHITE + (220,), width=scale)

    _centered_text(draw, width, 286 * scale, "НАЙДИ СВОЙ РАЙОН",
                   _font(6 * scale, True), (148, 163, 184, 235))
    return panel.convert("RGB").resize((164, 314), RESAMPLE)


def _make_wizard_small_image(icon: Image.Image) -> Image.Image:
    """Build the 55×55 logo used in the Inno Setup title area."""
    return icon.resize((55, 55), RESAMPLE)


def _make_preview(icons: dict[str, Image.Image]) -> Image.Image:
    preview = Image.new("RGBA", (2300, 780), (*NAVY_950, 255))
    preview.alpha_composite(_radial_glow(preview.size, (1150, 80), 780, BLUE, 70))
    draw = ImageDraw.Draw(preview, "RGBA")
    draw.text((88, 56), "Порайонка", font=_font(45, True), fill=WHITE + (255,))
    draw.text((88, 116), "Иконки установщиков · DARK", font=_font(22), fill=(148, 163, 184, 255))

    cards = (
        ("admin", "Администратор", "Полная редакция", VIOLET),
        ("user", "Пользователь", "Windows 10/11", TEAL),
        ("web", "User Web", "Windows 7", CYAN),
        ("admin_web", "Админ Web", "Windows 7", VIOLET),
    )
    x = 88
    for key, title, subtitle, accent in cards:
        card = (x, 190, x + 500, 670)
        draw.rounded_rectangle(card, radius=36, fill=(15, 28, 58, 220), outline=(*accent, 100), width=3)
        icon = icons[key].resize((310, 310), RESAMPLE)
        preview.paste(icon, (x + 95, 218), icon)
        draw.text((x + 38, 548), title, font=_font(25, True), fill=WHITE + (255,))
        draw.text((x + 38, 590), subtitle, font=_font(18), fill=(148, 163, 184, 255))
        draw.rounded_rectangle((x + 38, 630, x + 150, 637), radius=4, fill=(*accent, 255))
        x += 562

    # Small-size proof: the actual generated rasters, not a vector simulation.
    draw.text((88, 716), "Проверка читаемости:", font=_font(17), fill=(148, 163, 184, 255))
    sx = 300
    for side in (16, 24, 32, 48, 64):
        small = icons["admin"].resize((side, side), RESAMPLE)
        preview.paste(small, (sx, 704 + (64-side)//2), small)
        draw.text((sx + side + 8, 723), str(side), font=_font(13), fill=(100, 116, 139, 255))
        sx += side + 60
    return preview


def _make_installer_preview(
    icon_preview: Image.Image,
    wizard: Image.Image,
    wizard_small: Image.Image,
) -> Image.Image:
    """Combine the icon sheet and wizard artwork into one review image."""
    preview = Image.new("RGBA", (2300, 1400), (*NAVY_950, 255))
    preview.alpha_composite(icon_preview)
    preview.alpha_composite(_radial_glow(preview.size, (1450, 1160), 620, VIOLET, 42))
    draw = ImageDraw.Draw(preview, "RGBA")
    draw.text((88, 820), "Графика мастера установки", font=_font(34, True),
              fill=WHITE + (255,))
    draw.text((88, 868), "Фактические пропорции Inno Setup · 164×314 и 55×55",
              font=_font(18), fill=(148, 163, 184, 255))

    # Side artwork at 150% for convenient inspection.
    side = wizard.resize((246, 471), RESAMPLE)
    preview.paste(side, (88, 915))
    draw.rounded_rectangle((77, 904, 345, 1397), radius=18,
                           outline=(*BLUE, 105), width=3)

    # A restrained mock wizard header proves the small logo at actual size.
    window = (410, 915, 1712, 1304)
    draw.rounded_rectangle(window, radius=25, fill=(15, 23, 42, 245),
                           outline=(71, 85, 105, 255), width=3)
    draw.rounded_rectangle((412, 917, 1710, 1022), radius=23,
                           fill=(30, 41, 59, 255))
    draw.rectangle((412, 990, 1710, 1022), fill=(30, 41, 59, 255))
    draw.text((456, 944), "Установка Порайонка 2.0", font=_font(24, True),
              fill=WHITE + (255,))
    draw.text((456, 979), "DARK FINAL", font=_font(13, True),
              fill=(*BLUE_LIGHT, 255))
    preview.paste(wizard_small, (1620, 940), wizard_small)
    draw.text((456, 1074), "Добро пожаловать в мастер установки",
              font=_font(23, True), fill=WHITE + (255,))
    draw.text((456, 1122), "Редакции различаются иконками и цветными бейджами.",
              font=_font(17), fill=(148, 163, 184, 255))
    draw.rounded_rectangle((1450, 1226, 1660, 1272), radius=12,
                           fill=(*BLUE, 255))
    draw.text((1503, 1238), "Далее", font=_font(16, True), fill=WHITE + (255,))

    # Enlarged small mark, explicitly labelled so it is not mistaken for output size.
    draw.rounded_rectangle((1015, 1070, 1345, 1275), radius=24,
                           fill=(2, 6, 23, 150), outline=(*CYAN, 55), width=2)
    enlarged = wizard_small.resize((150, 150), RESAMPLE)
    preview.paste(enlarged, (1050, 1094), enlarged)
    draw.text((1216, 1134), "55×55", font=_font(18, True), fill=WHITE + (255,))
    draw.text((1216, 1164), "увеличено", font=_font(14),
              fill=(100, 116, 139, 255))
    return preview


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    variants = {
        "icon": build_icon(),
        "icon_admin": build_icon("admin"),
        "icon_user": build_icon("user"),
        "icon_user_web": build_icon("web"),
        "icon_admin_web": build_icon("admin_web"),
    }
    for stem, image in variants.items():
        image.save(HERE / f"{stem}.png", optimize=True)
        _save_ico(image, HERE / f"{stem}.ico")

    preview_icons = {
        "admin": variants["icon_admin"],
        "user": variants["icon_user"],
        "web": variants["icon_user_web"],
        "admin_web": variants["icon_admin_web"],
    }
    icon_preview = _make_preview(preview_icons)
    icon_preview.save(HERE / "icons_preview.png", optimize=True)

    wizard = _make_wizard_image(variants["icon"])
    wizard_small = _make_wizard_small_image(variants["icon"])
    wizard.save(HERE / "wizard_image.png", optimize=True)
    wizard_small.save(HERE / "wizard_small_image.png", optimize=True)
    _make_installer_preview(icon_preview, wizard, wizard_small).save(
        HERE / "installer_artwork_preview.png", optimize=True
    )
    print(
        f"Generated {len(variants)} icon PNG + {len(variants)} ICO, "
        f"2 wizard PNG and 2 previews in {HERE}"
    )


if __name__ == "__main__":
    main()
