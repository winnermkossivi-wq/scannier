#!/usr/bin/env python3
"""
Generate PWA icons using only Pillow (no system dependencies).
Run: python generate_icons_simple.py
"""
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw, ImageFont

ICON_SIZES = [
    16, 32, 72, 96, 128, 144, 152, 167, 180, 192, 384, 512
]

SPLASH_SIZES = [
    (640, 1136),
    (750, 1334),
    (1125, 2436),
    (1242, 2688),
    (1536, 2048),
    (1668, 2388),
    (1668, 2520),
]

BASE_DIR = Path(__file__).parent
ICONS_DIR = BASE_DIR / "icons"
ICONS_DIR.mkdir(exist_ok=True)

PRIMARY_GREEN = (21, 128, 61)
DARK_GREEN = (22, 101, 52)
WHITE = (255, 255, 255)
SCAN_GREEN = (21, 128, 61)

def create_gradient_background(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    for y in range(size):
        ratio = y / size
        r = int(PRIMARY_GREEN[0] * (1 - ratio) + DARK_GREEN[0] * ratio)
        g = int(PRIMARY_GREEN[1] * (1 - ratio) + DARK_GREEN[1] * ratio)
        b = int(PRIMARY_GREEN[2] * (1 - ratio) + DARK_GREEN[2] * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    
    return img

def draw_rounded_rect(draw, bbox, radius, fill):
    x1, y1, x2, y2 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=fill)

def generate_icon(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    padding = max(4, size // 32)
    corner_radius = max(8, size // 5)
    inner_rect = [padding, padding, size - padding, size - padding]
    
    for y in range(padding, size - padding):
        ratio = (y - padding) / (size - 2 * padding)
        r = int(PRIMARY_GREEN[0] * (1 - ratio) + DARK_GREEN[0] * ratio)
        g = int(PRIMARY_GREEN[1] * (1 - ratio) + DARK_GREEN[1] * ratio)
        b = int(PRIMARY_GREEN[2] * (1 - ratio) + DARK_GREEN[2] * ratio)
        draw.line([(padding, y), (size - padding, y)], fill=(r, g, b, 255))
    
    draw.rounded_rectangle(inner_rect, radius=corner_radius, fill=None, outline=None)
    
    barcode_top = int(size * 0.2)
    barcode_bottom = int(size * 0.7)
    barcode_height = barcode_bottom - barcode_top
    center_x = size // 2
    
    bar_widths = [4, 2, 3, 2, 5, 2, 4, 2, 3, 2, 4, 3, 2, 5, 4]
    total_width = sum(w * size // 100 for w in bar_widths) + len(bar_widths) * (size // 200)
    start_x = center_x - total_width // 2
    
    x = start_x
    for bw in bar_widths:
        bw_px = max(1, bw * size // 100)
        draw.rounded_rectangle(
            [x, barcode_top, x + bw_px, barcode_bottom],
            radius=max(1, bw_px // 2),
            fill=WHITE
        )
        x += bw_px + max(1, size // 200)
    
    scan_y = size // 2
    scan_left = center_x - int(size * 0.15)
    scan_right = center_x + int(size * 0.15)
    scan_width = max(2, size // 80)
    draw.line([(scan_left, scan_y), (scan_right, scan_y)], fill=SCAN_GREEN, width=scan_width)
    
    try:
        font_size = int(size * 0.18)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(size * 0.18))
        except:
            font = ImageFont.load_default()
    
    text = "S"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size - text_width) // 2
    text_y = int(size * 0.72) - text_height // 2
    
    draw.text((text_x, text_y), text, fill=WHITE, font=font)
    
    output_path = ICONS_DIR / f"icon-{size}x{size}.png"
    img.save(output_path, 'PNG')
    print(f"Generated: {output_path.name}")

def generate_splash(width, height):
    img = Image.new('RGB', (width, height), PRIMARY_GREEN)
    draw = ImageDraw.Draw(img)
    
    for y in range(height):
        ratio = y / height
        r = int(PRIMARY_GREEN[0] * (1 - ratio) + DARK_GREEN[0] * ratio)
        g = int(PRIMARY_GREEN[1] * (1 - ratio) + DARK_GREEN[1] * ratio)
        b = int(PRIMARY_GREEN[2] * (1 - ratio) + DARK_GREEN[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    icon_size = min(width, height) // 3
    icon_x = (width - icon_size) // 2
    icon_y = (height - icon_size) // 2 - 40
    
    draw.rounded_rectangle(
        [icon_x, icon_y, icon_x + icon_size, icon_y + icon_size],
        radius=icon_size // 5,
        fill=DARK_GREEN
    )
    
    barcode_top = icon_y + int(icon_size * 0.15)
    barcode_bottom = icon_y + int(icon_size * 0.65)
    center_x = width // 2
    
    bar_widths = [4, 2, 3, 2, 5, 2, 4, 2, 3, 2, 4, 3, 2, 5, 4]
    total_width = sum(w * icon_size // 100 for w in bar_widths)
    start_x = center_x - total_width // 2
    
    x = start_x
    for bw in bar_widths:
        bw_px = max(1, bw * icon_size // 100)
        draw.rounded_rectangle(
            [x, barcode_top, x + bw_px, barcode_bottom],
            radius=max(1, bw_px // 2),
            fill=WHITE
        )
        x += bw_px + max(1, icon_size // 150)
    
    try:
        font_size = icon_size // 2
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    text = "S"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (width - text_width) // 2
    text_y = icon_y + icon_size + 20
    
    draw.text((text_x, text_y), text, fill=WHITE, font=font)
    
    output_path = ICONS_DIR / f"splash-{width}x{height}.png"
    img.save(output_path, 'PNG')
    print(f"Generated: {output_path.name}")

def main():
    print("Generating PWA icons with Pillow...")
    
    for size in ICON_SIZES:
        generate_icon(size)
    
    print("\nGenerating iOS splash screens...")
    for width, height in SPLASH_SIZES:
        generate_splash(width, height)
    
    maskable_path = ICONS_DIR / "icon-512x512.png"
    if maskable_path.exists():
        import shutil
        shutil.copy(maskable_path, ICONS_DIR / "icon-512x512-maskable.png")
        print("Created maskable icon copy")
    
    icon_167 = ICONS_DIR / "icon-167x167.png"
    if icon_167.exists():
        import shutil
        shutil.copy(icon_167, ICONS_DIR / "icon-167x167.png")
    
    print("\nDone! Icons generated in:", ICONS_DIR)

if __name__ == "__main__":
    main()