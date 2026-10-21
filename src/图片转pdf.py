
import os
import re
import sys
import tempfile
from datetime import datetime

from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas



# 支持的图片扩展名
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


from pathlib import Path

def get_subfolder_info(input_dir):
    """
    遍历 input_dir 下的所有子文件夹，返回包含完整路径和预期PDF名称的列表。
    """
    input_path = Path(input_dir)
    
    # 检查输入路径是否存在且为文件夹
    if not input_path.exists() or not input_path.is_dir():
        raise ValueError(f"提供的路径不存在或不是一个文件夹: {input_dir}")
        
    result_list = []
    
    # iterdir() 遍历当前目录下的直接子项
    for child in input_path.iterdir():
        if child.is_dir():
            # 构造 output_pdf_path: [父文件夹名]_[子文件夹名].pdf
            parent_name = input_path.name
            child_name = child.name
            output_pdf_name = f"{input_dir}/{child_name}.pdf"
            
            result_list.append({
                "input_child_dir": str(child.resolve()),  # 子文件夹的绝对完整路径
                "output_pdf_path": output_pdf_name        # 生成的PDF文件名
            })
            
    return result_list

def natural_key(name):
    """自然排序的排序键: 把文件名里的数字段当作整数比较。
    例如 page2.jpg < page10.jpg。"""
    parts = re.split(r"(\d+)", name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def collect_images(image_dir):
    """列出文件夹内(不含子目录)的图片, 按自然排序返回完整路径列表。"""
    if not os.path.isdir(image_dir):
        raise NotADirectoryError(f"图片文件夹不存在: {image_dir}")

    files = []
    for name in os.listdir(image_dir):
        full = os.path.join(image_dir, name)
        if os.path.isfile(full) and os.path.splitext(name)[1].lower() in IMAGE_EXTS:
            files.append(name)

    files.sort(key=natural_key)
    return [os.path.join(image_dir, n) for n in files]


def prepare_image(path):
    """把图片统一转成 reportlab 可嵌入的 RGB/CMYK 图片路径。
    透明/调色板/灰度 PNG 等会先转存为临时 JPEG(白底), 避免嵌入报错。"""
    mode = Image.open(path).mode
    if mode in ("RGB", "CMYK", "L"):
        # L(灰度) 与 CMYK reportlab 均可直接嵌入; 但灰度用 JPEG 更稳妥, 这里保留原始交给 reportlab
        if mode == "L":
            tmp = os.path.join(tempfile.gettempdir(), os.path.basename(path) + ".tmp.jpg")
            Image.open(path).convert("RGB").save(tmp, "JPEG", quality=95)
            return tmp, True
        return path, False

    # RGBA / P / LA / 1 等: 转 RGB, 透明区域填白
    tmp = os.path.join(tempfile.gettempdir(), os.path.basename(path) + ".tmp.jpg")
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    img.save(tmp, "JPEG", quality=95)
    return tmp, True


def images_to_pdf(image_dir, output_pdf, dpi=72.0):

    image_paths = collect_images(image_dir)
    if not image_paths:
        print(f"[错误] 在文件夹中未找到图片: {image_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"共找到 {len(image_paths)} 张图片, 排序如下:")
    for i, p in enumerate(image_paths, 1):
        print(f"  {i:>3}. {os.path.basename(p)}")


    out_dir = os.path.dirname(os.path.abspath(output_pdf))
    os.makedirs(out_dir, exist_ok=True)

    scale = 72.0 / dpi


    c = canvas.Canvas(output_pdf)
    temp_files = []
    try:
        for p in image_paths:
            draw_path, is_temp = prepare_image(p)
            if is_temp:
                temp_files.append(draw_path)

            with Image.open(p) as im:
                w_px, h_px = im.size

            w_pt = max(1.0, w_px * scale)
            h_pt = max(1.0, h_px * scale)

            c.setPageSize((w_pt, h_pt))
            c.drawImage(draw_path, 0, 0, width=w_pt, height=h_pt,
                        preserveAspectRatio=False, mask=None)
            c.showPage()

        c.save()
    finally:
        for t in temp_files:
            try:
                os.remove(t)
            except OSError:
                pass

    print(f"已生成 PDF: {os.path.abspath(output_pdf)}")



if __name__ == "__main__":
    image_dir = "/Users/teacher/Desktop/111/000"
    batch = True
    dpi = 300



    if not batch:

        now = datetime.now()
        # formatted_time = now.strftime("%Y年%m月%d日%H时%M分%S秒") + f"{now.microsecond // 1000:03d}"
        formatted_time = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
        output_pdf = f"{image_dir}_{formatted_time}.pdf"
        images_to_pdf(
            image_dir=image_dir, 
            output_pdf=output_pdf, 
            dpi = dpi
        )
    else:
        result_list = get_subfolder_info(image_dir)
        print(f"共发现 {len(result_list)} 个子文件夹，开始处理：\n")

        # 遍历列表中的每一个字典
        for item in result_list:
            # 通过键名获取对应的值
            source_dir = item["input_child_dir"]
            target_pdf = item["output_pdf_path"]

            images_to_pdf(
                image_dir=source_dir, 
                output_pdf=target_pdf, 
                dpi = dpi
            )