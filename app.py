import os
import io
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, send_file, jsonify
from mard_colors import MARD_PALETTE

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def build_palette_arrays(palette):
    """将调色板转为 numpy 数组，用于向量化计算"""
    codes = list(palette.keys())
    colors = np.array([palette[c] for c in codes], dtype=np.float32)
    return codes, colors


def find_nearest_colors_batch(pixels_rgb, palette_codes, palette_colors):
    """批量找到每个像素最近的颜色（向量化，分块避免内存溢出）"""
    chunk_size = 10000
    all_indices = []
    pixels = pixels_rgb.astype(np.float32)
    for start in range(0, len(pixels), chunk_size):
        chunk = pixels[start:start + chunk_size]
        diff = chunk[:, np.newaxis, :] - palette_colors[np.newaxis, :, :]
        dists = np.sum(diff ** 2, axis=2)
        all_indices.append(np.argmin(dists, axis=1))
    indices = np.concatenate(all_indices)
    return [palette_codes[i] for i in indices]


def image_to_beads(img, grid_width, grid_height, max_colors=60, bg_transparent=True):
    """将图像转换为拼豆设计数据，图片按比例缩放居中，空余留白"""
    img = img.convert('RGBA')
    img_w, img_h = img.size

    # 按比例缩放，适应网格，不拉伸
    scale = min(grid_width / img_w, grid_height / img_h)
    fit_w = max(1, round(img_w * scale))
    fit_h = max(1, round(img_h * scale))
    img_resized = img.resize((fit_w, fit_h), Image.LANCZOS)
    pixels = np.array(img_resized)

    # 居中偏移
    offset_x = (grid_width - fit_w) // 2
    offset_y = (grid_height - fit_h) // 2

    alpha = pixels[:, :, 3]
    rgb = pixels[:, :, :3]

    # 标记透明像素
    if bg_transparent:
        transparent_mask = alpha < 128
    else:
        transparent_mask = np.zeros((fit_h, fit_w), dtype=bool)

    opaque_mask = ~transparent_mask
    opaque_rgb = rgb[opaque_mask]

    # 第一轮：向量化颜色匹配
    palette_codes, palette_colors = build_palette_arrays(MARD_PALETTE)
    matched_codes = find_nearest_colors_batch(opaque_rgb, palette_codes, palette_colors)

    # 写入 grid_data（整个画布初始化为 None）
    grid_data = [[None] * grid_width for _ in range(grid_height)]
    color_count = {}
    idx = 0
    for y in range(fit_h):
        for x in range(fit_w):
            if opaque_mask[y, x]:
                code = matched_codes[idx]
                grid_data[offset_y + y][offset_x + x] = code
                color_count[code] = color_count.get(code, 0) + 1
                idx += 1

    # 限制最大颜色数
    if len(color_count) > max_colors:
        sorted_colors = sorted(color_count.items(), key=lambda x: -x[1])
        keep_colors = set(code for code, _ in sorted_colors[:max_colors])
        reduced_palette = {k: v for k, v in MARD_PALETTE.items() if k in keep_colors}

        r_codes, r_colors = build_palette_arrays(reduced_palette)
        matched_codes = find_nearest_colors_batch(opaque_rgb, r_codes, r_colors)

        grid_data = [[None] * grid_width for _ in range(grid_height)]
        color_count = {}
        idx = 0
        for y in range(fit_h):
            for x in range(fit_w):
                if opaque_mask[y, x]:
                    code = matched_codes[idx]
                    grid_data[offset_y + y][offset_x + x] = code
                    color_count[code] = color_count.get(code, 0) + 1
                    idx += 1

    return grid_data, color_count


def render_pattern(grid_data, color_count, grid_width, grid_height, show_codes=True):
    """渲染拼豆设计图为PNG图片"""
    # 大尺寸时自动缩小格子
    if max(grid_width, grid_height) > 200:
        cell_size = 12
    elif max(grid_width, grid_height) > 100:
        cell_size = 20
    else:
        cell_size = 36
    header_size = 24  # 行列标号区域
    legend_height = max(100, (math.ceil(len(color_count) / 6) + 1) * 30)

    img_width = header_size + grid_width * cell_size + 20
    img_height = header_size + grid_height * cell_size + legend_height + 40

    img = Image.new('RGB', (img_width, img_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 尝试加载字体
    try:
        font_small = ImageFont.truetype("arial.ttf", 9)
        font_num = ImageFont.truetype("arial.ttf", 10)
        font_legend = ImageFont.truetype("arial.ttf", 11)
        font_title = ImageFont.truetype("arial.ttf", 14)
    except:
        font_small = ImageFont.load_default()
        font_num = font_small
        font_legend = font_small
        font_title = font_small

    offset_x = header_size
    offset_y = header_size

    # 绘制行列编号
    for i in range(1, grid_width + 1):
        x = offset_x + (i - 1) * cell_size + cell_size // 2
        draw.text((x, 5), str(i), fill=(100, 100, 100), font=font_num, anchor="mt")
        draw.text((x, offset_y + grid_height * cell_size + 5), str(i),
                  fill=(100, 100, 100), font=font_num, anchor="mt")

    for j in range(1, grid_height + 1):
        y = offset_y + (j - 1) * cell_size + cell_size // 2
        draw.text((5, y), str(j), fill=(100, 100, 100), font=font_num, anchor="lm")

    # 绘制格子
    for y in range(grid_height):
        for x in range(grid_width):
            code = grid_data[y][x]
            px = offset_x + x * cell_size
            py = offset_y + y * cell_size

            if code is None:
                # 背景格子 - 浅色交叉线
                draw.rectangle([px, py, px + cell_size, py + cell_size],
                               fill=(250, 248, 245), outline=(220, 218, 215))
            else:
                color = MARD_PALETTE[code]
                draw.rectangle([px, py, px + cell_size, py + cell_size],
                               fill=color, outline=(180, 180, 180))

                # 在格子内显示色号
                if show_codes:
                    # 根据背景亮度选择文字颜色
                    brightness = (color[0] * 299 + color[1] * 587 + color[2] * 114) / 1000
                    text_color = (255, 255, 255) if brightness < 128 else (0, 0, 0)
                    cx = px + cell_size // 2
                    cy = py + cell_size // 2
                    draw.text((cx, cy), code, fill=text_color, font=font_small, anchor="mm")

    # 绘制主网格线（每5格加粗）
    for i in range(grid_width + 1):
        x = offset_x + i * cell_size
        width = 2 if i % 5 == 0 else 1
        color = (80, 80, 80) if i % 5 == 0 else (200, 200, 200)
        draw.line([(x, offset_y), (x, offset_y + grid_height * cell_size)],
                  fill=color, width=width)

    for j in range(grid_height + 1):
        y = offset_y + j * cell_size
        width = 2 if j % 5 == 0 else 1
        color = (80, 80, 80) if j % 5 == 0 else (200, 200, 200)
        draw.line([(offset_x, y), (offset_x + grid_width * cell_size, y)],
                  fill=color, width=width)

    # 绘制图例/色号统计
    legend_y = offset_y + grid_height * cell_size + 30
    total_beads = sum(color_count.values())
    draw.text((offset_x, legend_y - 20),
              f"拼豆设计图 · 总计 {total_beads} 颗",
              fill=(50, 50, 50), font=font_title)

    # 按使用量排序的颜色图例
    sorted_legend = sorted(color_count.items(), key=lambda x: -x[1])
    cols = 6
    legend_cell_w = (img_width - 40) // cols
    legend_cell_h = 26

    for idx, (code, count) in enumerate(sorted_legend):
        col = idx % cols
        row = idx // cols
        lx = offset_x + col * legend_cell_w
        ly = legend_y + row * legend_cell_h

        # 色块
        color = MARD_PALETTE[code]
        draw.rectangle([lx, ly, lx + 20, ly + 18], fill=color, outline=(100, 100, 100))

        # 色号和数量
        brightness = (color[0] * 299 + color[1] * 587 + color[2] * 114) / 1000
        inner_color = (255, 255, 255) if brightness < 128 else (0, 0, 0)
        draw.text((lx + 10, ly + 9), code, fill=inner_color, font=font_small, anchor="mm")
        draw.text((lx + 24, ly + 9), f"{code} ({count})",
                  fill=(50, 50, 50), font=font_legend, anchor="lm")

    return img


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    if 'image' not in request.files:
        return jsonify({'error': '请上传图片'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    grid_width = min(int(request.form.get('grid_width', 29)), 500)
    grid_height = min(int(request.form.get('grid_height', 29)), 500)
    max_colors = int(request.form.get('max_colors', 30))
    show_codes = request.form.get('show_codes', 'true') == 'true'

    try:
        img = Image.open(file.stream)
    except Exception as e:
        return jsonify({'error': f'无法读取图片: {str(e)}'}), 400

    # 转换
    grid_data, color_count = image_to_beads(img, grid_width, grid_height, max_colors)

    # 渲染
    result_img = render_pattern(grid_data, color_count, grid_width, grid_height, show_codes)

    # 保存到内存并返回
    buf = io.BytesIO()
    result_img.save(buf, format='PNG', quality=95)
    buf.seek(0)

    return send_file(buf, mimetype='image/png', as_attachment=False,
                     download_name='bead_pattern.png')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
