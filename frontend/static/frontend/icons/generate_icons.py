#!/usr/bin/env python3
"""
Generate PWA icons from SVG template.
Requires: pip install pillow cairosvg
Run: python generate_icons.py
"""
import os
import sys
from pathlib import Path

try:
    import cairosvg
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "cairosvg"])
    import cairosvg
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

SVG_TEMPLATE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#15803d;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#166534;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect x="16" y="16" width="480" height="480" rx="96" fill="url(#bgGrad)"/>
  <g transform="translate(256, 256)">
    <g fill="#ffffff" opacity="0.95">
      <rect x="-70" y="-80" width="4" height="160" rx="2"/>
      <rect x="-60" y="-80" width="2" height="160" rx="1"/>
      <rect x="-52" y="-80" width="3" height="160" rx="1.5"/>
      <rect x="-42" y="-80" width="2" height="160" rx="1"/>
      <rect x="-34" y="-80" width="5" height="160" rx="2.5"/>
      <rect x="-22" y="-80" width="2" height="160" rx="1"/>
      <rect x="-14" y="-80" width="4" height="160" rx="2"/>
      <rect x="-4" y="-80" width="2" height="160" rx="1"/>
      <rect x="6" y="-80" width="3" height="160" rx="1.5"/>
      <rect x="16" y="-80" width="2" height="160" rx="1"/>
      <rect x="26" y="-80" width="4" height="160" rx="2"/>
      <rect x="36" y="-80" width="3" height="160" rx="1.5"/>
      <rect x="46" y="-80" width="2" height="160" rx="1"/>
      <rect x="56" y="-80" width="5" height="160" rx="2.5"/>
      <rect x="66" y="-80" width="4" height="160" rx="2"/>
    </g>
    <line x1="-80" y1="0" x2="80" y2="0" stroke="#15803d" stroke-width="6" stroke-linecap="round" opacity="0.8"/>
  </g>
  <text x="256" y="360" font-family="system-ui, sans-serif" font-size="80" font-weight="800" fill="#ffffff" text-anchor="middle" opacity="0.95">S</text>
</svg>'''

def generate_icon(size):
    svg_content = SVG_TEMPLATE.format(size=size)
    output_path = ICONS_DIR / f"icon-{size}x{size}.png"
    cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), write_to=str(output_path), output_width=size, output_height=size)
    print(f"Generated: {output_path.name}")

def generate_splash(width, height):
    img = Image.new('RGB', (width, height), '#15803d')
    draw = ImageDraw.Draw(img)
    
    icon_size = min(width, height) // 3
    icon_x = (width - icon_size) // 2
    icon_y = (height - icon_size) // 2 - 40
    
    draw.rounded_rectangle(
        [icon_x, icon_y, icon_x + icon_size, icon_y + icon_size],
        radius=icon_size // 5,
        fill='#166534'
    )
    
    bar_width = icon_size // 20
    bar_height = icon_size * 0.6
    bar_x = icon_x + icon_size // 2 - (7 * bar_width)
    bar_y = icon_y + (icon_size - bar_height) // 2
    
    bar_widths = [4, 2, 3, 2, 5, 2, 4, 2, 3, 2, 4, 3, 2, 5, 4]
    
    for i, bw in enumerate(bar_widths):
        x = bar_x + i * (bar_width * 1.5)
        bw_px = max(1, int(bw * icon_size / 100))
        draw.rounded_rectangle(
            [x, bar_y, x + bw_px, bar_y + bar_height],
            radius=bw_px // 2,
            fill='white'
        )
    
    try:
        font_size = icon_size // 2
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text = "S"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (width - text_width) // 2
    text_y = icon_y + icon_size + 20
    
    draw.text((text_x, text_y), text, fill='white', font=font)
    
    output_path = ICONS_DIR / f"splash-{width}x{height}.png"
    img.save(output_path)
    print(f"Generated: {output_path.name}")

def main():
    print("Generating PWA icons...")
    
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
    
    print("\nDone! Icons generated in:", ICONS_DIR)

if __name__ == "__main__":
    main()