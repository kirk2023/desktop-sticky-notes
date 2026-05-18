#!/usr/bin/env python3
"""生成专业风格的桌面便签应用图标"""
import os
from PIL import Image, ImageDraw

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def create_icon():
    size = 256

    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. 圆角背景 - 深蓝色专业风格
    draw.rounded_rectangle([(0, 0), (size-1, size-1)], radius=48,
                           fill=(44, 62, 80))

    # 2. 淡黄色便签
    note_points = [(55, 60), (175, 60), (175, 200), (95, 200), (55, 170)]
    draw.polygon(note_points, fill=(255, 249, 196))

    # 3. 便签上的线条
    line_color = (189, 195, 199)
    for y in [100, 130, 160]:
        draw.line([(75, y), (155, y)], fill=line_color, width=3)

    # 4. 红色图钉
    draw.ellipse([(125, 68), (147, 90)], fill=(231, 76, 60))
    draw.ellipse([(131, 74), (141, 84)], fill=(192, 57, 43))
    draw.ellipse([(133, 76), (139, 80)], fill=(255, 255, 255, 180))

    # 保存
    img.save('logo.png')
    print("Created logo.png")

    for s in [16, 24, 32, 48, 64, 128, 256]:
        small = img.resize((s, s), Image.Resampling.LANCZOS)
        small.save(f'logo_{s}.png')
        print(f"Created logo_{s}.png")

    # ICO
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    ico_images = [img.resize((s, s), Image.Resampling.LANCZOS) for s in ico_sizes]
    ico_images[0].save('logo.ico', format='ICO',
                       sizes=[(s, s) for s in ico_sizes],
                       append_images=ico_images[1:])
    print("Created logo.ico")

if __name__ == '__main__':
    create_icon()
    print("Done!")