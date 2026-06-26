import os
from itertools import islice
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from PIL import Image

# ================= 纯函数层 (Pure Functions) =================

def get_sorted_images(folder_path):
    """获取文件夹内的图片并按文件名排序（纯函数：无副作用）"""
    valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
    images = [
        os.path.join(folder_path, f) 
        for f in os.listdir(folder_path) 
        if os.path.splitext(f)[1].lower() in valid_extensions
    ]
    return sorted(images, key=os.path.basename)

def chunk_list(lst, chunk_size):
    """将列表按指定大小分块（纯函数：返回生成器，不修改原列表）"""
    it = iter(lst)
    return iter(lambda: tuple(islice(it, chunk_size)), ())

def calculate_layout(page_size, margins, cols, rows, h_gap, v_gap):
    """计算布局参数（纯函数：输入配置，输出布局尺寸）"""
    page_width, page_height = page_size
    margin_x, margin_y = margins
    
    available_width = page_width - 2 * margin_x
    available_height = page_height - 2 * margin_y
    
    max_img_width = (available_width - (cols - 1) * h_gap) / cols
    max_img_height = (available_height - (rows - 1) * v_gap) / rows
    
    return {
        "page_width": page_width,
        "page_height": page_height,
        "margin_x": margin_x,
        "margin_y": margin_y,
        "max_img_width": max_img_width,
        "max_img_height": max_img_height,
        "cols": cols,
        "rows": rows,
        "h_gap": h_gap,
        "v_gap": v_gap
    }

def calculate_draw_dimensions(img_path, max_width, max_height):
    """计算图片等比缩放后的实际绘制尺寸和居中偏移量（纯函数）"""
    try:
        img = Image.open(img_path)
        img_w, img_h = img.size
        aspect_ratio = img_w / img_h
        
        if aspect_ratio > (max_width / max_height):
            draw_width = max_width
            draw_height = max_width / aspect_ratio
        else:
            draw_height = max_height
            draw_width = max_height * aspect_ratio
            
        x_offset = (max_width - draw_width) / 2
        y_offset = (max_height - draw_height) / 2
        
        return draw_width, draw_height, x_offset, y_offset
    except Exception:
        return 0, 0, 0, 0

def get_image_coordinates(layout, col_idx, row_idx):
    """根据网格索引计算图片左下角坐标（纯函数）"""
    x = layout["margin_x"] + col_idx * (layout["max_img_width"] + layout["h_gap"])
    y = (layout["page_height"] - layout["margin_y"] 
         - (row_idx + 1) * layout["max_img_height"] 
         - row_idx * layout["v_gap"])
    return x, y

# ================= 副作用层 (Side Effects / I/O) =================

def draw_image_on_page(pdf_canvas, img_path, layout, col_idx, row_idx):
    """在画布上绘制单张图片（包含副作用）"""
    x, y = get_image_coordinates(layout, col_idx, row_idx)
    draw_w, draw_h, x_off, y_off = calculate_draw_dimensions(
        img_path, layout["max_img_width"], layout["max_img_height"]
    )
    
    if draw_w > 0:
        pdf_canvas.drawImage(
            img_path, x + x_off, y + y_off, 
            width=draw_w, height=draw_h, 
            preserveAspectRatio=True, mask='auto'
        )

def generate_pdf(image_folder, output_pdf, **kwargs):
    """
    生成 PDF 的主入口（组合纯函数与副作用）
    """
    # 1. 获取数据
    images = get_sorted_images(image_folder)
    if not images:
        print("⚠️ 未找到任何图片，请检查文件夹路径。")
        return

    # 2. 计算布局
    layout = calculate_layout(
        page_size=kwargs.get("page_size", A4),
        margins=kwargs.get("margins", (20*mm, 20*mm)),
        cols=kwargs.get("cols", 2),
        rows=kwargs.get("rows", 1),
        h_gap=kwargs.get("h_gap", 10*mm),
        v_gap=kwargs.get("v_gap", 10*mm)
    )

    # 3. 将图片列表按“每页数量”分块
    images_per_page = layout["cols"] * layout["rows"]
    pages_data = chunk_list(images, images_per_page)

    # 4. 创建画布并映射绘制操作
    c = canvas.Canvas(
            output_pdf, 
            pagesize=(layout["page_width"], layout["page_height"])
        )
    
    for page_images in pages_data:
        # 使用 map 和 enumerate 替代传统的 for 循环和计数器
        list(map(
            lambda args: draw_image_on_page(c, args[1], layout, args[0] % layout["cols"], args[0] // layout["cols"]),
            enumerate(page_images)
        ))
        c.showPage()

    c.save()
    print(f"✅ PDF 生成成功: {output_pdf}")


# ================= 使用示例 =================
if __name__ == "__main__":
    image_folder="/Users/teacher/Desktop/未命名文件夹 3/思凡尼2026图册_图片_1"

    output_dir = "/Users/teacher/Desktop/未命名文件夹 3/"
    output_path = os.path.join(output_dir, "output.pdf")
    generate_pdf(
        image_folder=image_folder,
        output_pdf=output_path,
        page_size=A4,
        margins=(15*mm, 15*mm),
        cols=2,
        rows=1,
        h_gap=10*mm,
        v_gap=10*mm
    )