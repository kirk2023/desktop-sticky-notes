#!/usr/bin/env python3
"""生成应用图标"""
import os
import struct
import base64

# 简单的ICO文件生成
def create_ico():
    """创建简单的ICO文件（基于PNG数据）"""
    # 使用简单的BMP格式创建图标
    # 这是最基础的实现

    # 256x256 32位RGBA位图
    width = 256
    height = 256
    bpp = 32

    # 创建像素数据（简化版：紫色背景+黄色便签）
    pixels = bytearray(width * height * 4)

    # 填充背景（紫渐变）
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 4
            r = int(102 + (118 - 102) * x / width)
            g = int(126 + (75 - 126) * x / width)
            b = int(234 + (162 - 234) * x / width)
            pixels[idx] = b      # Blue
            pixels[idx+1] = g    # Green
            pixels[idx+2] = r    # Red
            pixels[idx+3] = 255  # Alpha

    # 绘制便签（简化）
    center_x, center_y = 128, 140
    note_w, note_h = 100, 120

    # 黄色便签区域
    for y in range(center_y - note_h//2, center_y + note_h//2):
        for x in range(center_x - note_w//2, center_x + note_w//2):
            if 0 <= x < width and 0 <= y < height:
                idx = (y * width + x) * 4
                # 淡黄色
                pixels[idx] = 196     # B
                pixels[idx+1] = 235  # G
                pixels[idx+2] = 255  # R
                pixels[idx+3] = 255  # A

    # 红色图钉
    pin_x, pin_y = 140, 90
    for dy in range(-8, 8):
        for dx in range(-8, 8):
            if dx*dx + dy*dy <= 64:
                px, py = pin_x + dx, pin_y + dy
                if 0 <= px < width and 0 <= py < height:
                    idx = (py * width + px) * 4
                    pixels[idx] = 60       # B
                    pixels[idx+1] = 52     # G
                    pixels[idx+2] = 231    # R
                    pixels[idx+3] = 255    # A

    # ICO文件头
    ico_header = struct.pack('<HHH', 0, 1, 1)  # Reserved, Type(1=ICO), Count

    # 计算位图数据大小
    row_size = ((width * bpp + 31) // 32) * 4
    image_size = row_size * height + 40  # BITMAPINFOHEADER + pixel data

    # ICO目录项
    ico_entry = struct.pack('<BBBBHHII',
        0 if width < 256 else 255,   # Width
        0 if height < 256 else 255,  # Height
        0,               # Color count
        0,               # Reserved
        1,               # Color planes
        32,              # Bits per pixel
        image_size,      # Size of image data
        22               # Offset to image data
    )

    # BITMAPINFOHEADER
    bmp_header = struct.pack('<IIIHHIIIIII',
        40,             # Header size
        width,          # Width
        height * 2,     # Height (doubled for XOR/AND masks)
        1,              # Planes
        32,             # Bits per pixel
        0,              # Compression
        image_size - 40, # Image size
        0, 0, 0, 0     # XPels, YPels, ClrUsed, ClrImportant
    )

    # 翻转像素（上下颠倒）
    flipped = bytearray(len(pixels))
    for y in range(height):
        src_row = y * width * 4
        dst_row = (height - 1 - y) * width * 4
        flipped[dst_row:dst_row + width*4] = pixels[src_row:src_row + width*4]

    # 写入文件
    with open('logo_new.ico', 'wb') as f:
        f.write(ico_header)
        f.write(ico_entry)
        f.write(bmp_header)
        f.write(flipped)

    print("Created logo_new.ico")

def create_png():
    """使用PIL创建PNG图标"""
    try:
        from PIL import Image, ImageDraw

        # 创建256x256图像
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 绘制圆角背景
        draw.rounded_rectangle([(0, 0), (255, 255)], radius=48,
                               fill=(102, 126, 234))

        # 绘制便签
        points = [(60, 60), (180, 60), (180, 200), (90, 200), (60, 170)]
        draw.polygon(points, fill=(255, 249, 196))

        # 绘制线条
        for y in [100, 130, 160]:
            draw.line([(80, y), (160, y)], fill=(224, 224, 224), width=3)

        # 绘制图钉
        draw.ellipse([(130, 75), (150, 95)], fill=(231, 76, 60))
        draw.ellipse([(135, 80), (145, 90)], fill=(192, 57, 43))

        img.save('logo.png')
        print("Created logo.png")

        # 生成多尺寸版本
        for size in [16, 32, 48, 64, 128]:
            small = img.resize((size, size), Image.Resampling.LANCZOS)
            small.save(f'logo_{size}.png')

    except ImportError:
        print("PIL not available, skipping PNG")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    create_png()
    create_ico()
    print("Done!")