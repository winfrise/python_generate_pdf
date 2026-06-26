import os
import io
from functools import partial
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ================= 1. 纯函数：配置与数据准备 =================

def get_image_files(folder, supported_exts=('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')):
    """纯函数：获取并过滤文件夹中的图片路径，返回排序后的列表"""
    files = [
        os.path.join(folder, f) 
        for f in os.listdir(folder) 
        if os.path.splitext(f)[1].lower() in supported_exts
    ]
    return sorted(files)

def calculate_draw_area(page_size, margins):
    """纯函数：根据页面大小和边距，计算可用绘制区域的宽高"""
    page_width, page_height = page_size
    margin_left, margin_bottom, margin_right, margin_top = margins
    return (
        page_width - margin_left - margin_right,
        page_height - margin_top - margin_bottom
    )

# ================= 2. 纯函数：图片处理策略 =================

def _stretch(img, target_w, target_h):
    """策略1：撑满（不保持比例）"""
    return img.resize((int(target_w), int(target_h)), Image.LANCZOS)

def _fit(img, target_w, target_h):
    """策略2：保持比例最大完整显示（居中留白）"""
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h
    
    if img_ratio > target_ratio:
        new_w, new_h = int(target_w), int(target_w / img_ratio)
    else:
        new_h, new_w = int(target_h), int(target_h * img_ratio)
        
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    # 创建白色背景画布并居中粘贴
    canvas_img = Image.new('RGB', (int(target_w), int(target_h)), (255, 255, 255))
    canvas_img.paste(resized, ((int(target_w) - new_w) // 2, (int(target_h) - new_h) // 2))
    return canvas_img

def _cover(img, target_w, target_h):
    """策略3：保持比例撑满，居中裁剪"""
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h
    
    if img_ratio > target_ratio:
        new_h, new_w = int(target_h), int(target_h * img_ratio)
    else:
        new_w, new_h = int(target_w), int(target_w / img_ratio)
        
    resized = img.resize((new_w, int(new_h)), Image.LANCZOS)
    # 居中裁剪
    crop_x = (new_w - int(target_w)) // 2
    crop_y = (new_h - int(target_h)) // 2
    return resized.crop((crop_x, crop_y, crop_x + int(target_w), crop_y + int(target_h)))

# 策略映射表（避免复杂的 if-else 分支）
IMAGE_STRATEGIES = {
    1: _stretch,
    2: _fit,
    3: _cover
}

def process_image(img_path, draw_area, mode):
    """纯函数：读取图片，根据模式应用策略，返回处理后的 PIL Image"""
    img = Image.open(img_path).convert("RGB")
    strategy = IMAGE_STRATEGIES.get(mode, _fit)
    return strategy(img, *draw_area)

def image_to_bytes(img, fmt='JPEG'):
    """纯函数：将 PIL Image 转换为字节流"""
    byte_arr = io.BytesIO()
    img.save(byte_arr, format=fmt)
    byte_arr.seek(0)
    return byte_arr

# ================= 3. 副作用函数：PDF 生成 =================

def create_pdf_pipeline(pdf_path, page_size, margins, mode):
    """
    高阶函数：返回一个接收图片路径列表的函数（闭包）
    将 PDF 的副作用操作封装在内部
    """
    draw_area = calculate_draw_area(page_size, margins)
    margin_left, margin_bottom, _, _ = margins
    
    def _pipeline(image_files):
        c = canvas.Canvas(pdf_path, pagesize=page_size)
        
        # 使用 map 和 partial 组合处理流程
        process_and_convert = partial(process_image, draw_area=draw_area, mode=mode)
        
        for img_path in image_files:
            try:
                # 管道：读取路径 -> 处理图片 -> 转字节流 -> 写入 PDF
                processed_img = process_and_convert(img_path)
                img_reader = ImageReader(image_to_bytes(processed_img))

                img_start_x = margin_left
                img_start_y = margin_bottom
                img_width, img_height = draw_area

                c.drawImage(img_reader, img_start_x, img_start_y, img_width, img_height)
                c.showPage()
                print(f"[OK] {os.path.basename(img_path)}")
            except Exception as e:
                print(f"[ERROR] {img_path}: {e}")
                
        c.save()
        print(f"\nPDF 生成成功: {pdf_path}")
        
    return _pipeline

# ================= 4. 主执行入口 =================

if __name__ == "__main__":
    image_folder = "/Users/teacher/Desktop/未命名文件夹 3/思凡尼2026图册_图片_1"
    output_path = "/Users/teacher/Desktop/未命名文件夹 3/a4_output.pdf"
    # 1. 定义配置（数据与逻辑分离）
    config = {
        "folder": image_folder,
        "pdf_path": output_path,
        "page_size": A4,
        "margins": (0, 0, 0, 0),
        "mode": 1  # 1: 撑满, 2: 适应, 3: 裁剪撑满
    }

    # 2. 获取数据
    image_files = get_image_files(config["folder"])
    if not image_files:
        print("未找到图片！")
    else:
        # 3. 构建并执行管道
        # create_pdf_pipeline 返回一个纯数据驱动的转换函数
        pdf_converter = create_pdf_pipeline(
            config["pdf_path"], 
            config["page_size"], 
            config["margins"], 
            config["mode"]
        )
        
        # 4. 触发执行
        pdf_converter(image_files)