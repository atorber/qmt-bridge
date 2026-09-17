"""生成托盘 / 安装包使用的品牌图标。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


def _draw_logo(size: int = 256):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size * 0.06
    radius = size * 0.22
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=radius,
        fill=(79, 140, 255, 255),
    )
    try:
        font = ImageFont.truetype("segoeui.ttf", int(size * 0.52))
    except OSError:
        try:
            font = ImageFont.truetype("msyh.ttc", int(size * 0.48))
        except OSError:
            font = ImageFont.load_default()
    text = "Q"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1] - size * 0.03
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    return img


def tray_image(size: int = 64):
    """返回 pystray 可用的 PIL Image。"""
    return _draw_logo(size)


def write_icon_files(directory: Path) -> dict[str, Path]:
    """写出 png / ico，供安装器与快捷方式使用。"""
    directory.mkdir(parents=True, exist_ok=True)
    png_path = directory / "qmt-bridge.png"
    ico_path = directory / "qmt-bridge.ico"
    img = _draw_logo(256)
    img.save(png_path)
    img.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)],
    )
    return {"png": png_path, "ico": ico_path}


def png_bytes(size: int = 64) -> bytes:
    buf = BytesIO()
    _draw_logo(size).save(buf, format="PNG")
    return buf.getvalue()
