import re
import os
from itertools import groupby
from operator import itemgetter
from functools import reduce
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

# 建议在全局注册一次字体，避免重复注册报错
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FONT_DIR = os.path.join(BASE_DIR, "assets", "fonts")

    # 这里以 Windows 的黑体为例，Mac/Linux 请替换为对应路径
    pdfmetrics.registerFont(TTFont('SimHei', f'{FONT_DIR}/simhei.ttf'))
    pdfmetrics.registerFont(TTFont('SimSun', f'{FONT_DIR}/simsun.ttf'))
    DEFAULT_FONT = 'SimHei'
except:
    print("警告：未找到 simhei.ttf，中文可能无法正常显示")
    DEFAULT_FONT = 'Helvetica' 


# ------------------- 核心工具函数 ------------------- #
def extract_category(filepath: str) -> str:
    filename = os.path.basename(filepath)
    """从文件名中提取横杠前的类别名称"""
    match = re.match(r'^(.*?)-\d+\.jpeg$', filename)
    return match.group(1) if match else filename


def get_image_size(image_path: str) -> tuple[int, int]:
    """获取图片的原始宽度和高度"""
    from PIL import Image
    with Image.open(image_path) as img:
        return img.size


def calculate_layout(images: list[str], page_width: float, page_height: float, margin: float) -> list[dict]:
    """根据图片数量计算布局（返回每个图片的位置和尺寸信息）"""
    page_available_w = page_width - 2 * margin
    page_available_h = page_height - 2 * margin
    count = len(images)

    # 辅助函数：保持比例缩放图片到指定高度
    def scale_to_height(img_w, img_h, target_h):
        ratio = target_h / img_h
        return (img_w * ratio, target_h)

    # 辅助函数：保持比例缩放图片到指定宽度
    def scale_to_width(img_w, img_h, target_w):
        ratio = target_w / img_w
        return (target_w, img_h * ratio)


    def scale_to_fit(img_w, img_h, max_w, max_h):
        """
        计算图片在保持比例的情况下，适应目标区域(max_w, max_h)的最佳尺寸。
        类似于 CSS 中的 object-fit: contain
        """
        if img_w == 0 or img_h == 0:
            return (0, 0)
            
        # 计算宽高比
        ratio = img_w / img_h
        
        # 1. 假设先按宽度填满，计算此时的高度
        # 2. 假设先按高度填满，计算此时的宽度
        
        # 判断哪种方式会超出限制
        if max_w / max_h > ratio:
            # 容器比图片更"宽"，说明高度是瓶颈 -> 以高度为准
            new_h = max_h
            new_w = new_h * ratio
        else:
            # 容器比图片更"高"（或比例一致），说明宽度是瓶颈 -> 以宽度为准
            new_w = max_w
            new_h = new_w / ratio
            
        return (new_w, new_h)

    if count == 1:
        w, h = get_image_size(images[0])
        image_scaled_w, image_scaled_h = scale_to_fit(w, h, page_available_w, page_available_h)
        x = margin + (page_available_w - image_scaled_w) / 2
        y = page_height - margin - image_scaled_h
        return [{
            'path': images[0], 
            'x': x, 
            'y': y, 
            'width': image_scaled_w, 
            'height': image_scaled_h
        }]

    elif count == 2:
        half_space = 10
        half_h = page_available_h / 2

        positions = []
        for i, img in enumerate(images):
            w, h = get_image_size(img)
            scaled_w, scaled_h = scale_to_height(w, h, half_h - half_space)
            if i == 0:  # 左上角
                x = margin
                y = margin + half_h + half_space
            else:       # 右下角
                x = margin + page_available_w - scaled_w
                y = margin
            positions.append({'path': img, 'x': x, 'y': y, 'width': scaled_w, 'height': scaled_h})
        return positions

    elif count == 3:
        half_space = 10
        half_h = page_available_h / 2
        positions = []
        for i, img in enumerate(images):
            w, h = get_image_size(img)
            if i == 0:  # 左上角
                image_scaled_w, image_scaled_h = scale_to_height(w, h, half_h - half_space)
                x = margin
                y = page_height - margin - image_scaled_h
            elif i == 1:  # 右下角
                image_scaled_w, image_scaled_h = scale_to_height(w, h, half_h - half_space)
                x = page_width - margin - image_scaled_w
                y = margin
            elif i == 2:  # 右上角
                top_right_w = page_available_w - positions[0]['width'] - half_space # 右上角区域宽度
                image_scaled_w, image_scaled_h = scale_to_width(w, h, top_right_w)
                x = page_width - image_scaled_w - margin
                y = page_height - margin - image_scaled_h

            positions.append({'path': img, 'x': x, 'y': y, 'width': image_scaled_w, 'height': image_scaled_h})
        return positions

    elif count == 4:
        space = 10
        cell_w = (page_available_w - space) / 2 
        cell_h = (page_available_h - space) / 2
        positions = []
        for i, img in enumerate(images):
            image_w, image_h = get_image_size(img)
            image_scaled_w, image_scaled_h = scale_to_fit(image_w, image_h, cell_w, cell_h)
            row = i // 2
            col = i % 2

            x = margin + col * (cell_w + space)
            y = page_height - margin - row * (cell_h + space) - image_scaled_h
            positions.append({
                'path': img, 
                'x': x, 
                'y': y, 
                'width': image_scaled_w, 
                'height': image_scaled_h
            })
        return positions

    else:
        raise ValueError(f"不支持的图片数量：{count}（仅支持1-4张）")


def draw_images(c: canvas.Canvas, layout: list[dict]):
    """在画布上绘制所有图片"""
    for pos in layout:
        c.drawImage(pos['path'], pos['x'], pos['y'], width=pos['width'], height=pos['height'])



def draw_page_title(canvas, title_text, page_width, page_height, margin=20):
    """
    在页面顶部绘制类别标题
    
    Args:
        canvas: ReportLab 画布对象
        title_text: 要显示的标题字符串 (如 "901")
        page_width: 页面总宽度
        page_height: 页面总高度
        margin: 页边距 (默认 20)
    """
    # 1. 设置样式
    font_size = 18
    canvas.setFont(DEFAULT_FONT, font_size)
    canvas.setFillColorRGB(0.1, 0.1, 0.1)  # 深灰色，比纯黑更柔和
    
    # 2. 计算位置 (水平居中)
    text_width = canvas.stringWidth(title_text, DEFAULT_FONT, font_size)
    x = (page_width - text_width) / 2
    y = page_height - margin - 5      # 距离顶部 margin 下方一点
    
    # 3. 绘制文字
    canvas.drawString(x, y, title_text)
    
    # 4. (可选) 绘制一条装饰横线
    # line_y = y - 6                    # 横线在文字下方
    # canvas.setStrokeColorRGB(0.8, 0.8, 0.8) # 浅灰色线条
    # canvas.line(margin, line_y, page_width - margin, line_y)

# ------------------- 主流程函数 ------------------- #
def generate_pdf(image_dir: str, output_path: str, page_size=A4, margin=36):
    """生成PDF的主函数"""
    import os
    # 1. 获取目录下所有JPEG图片并排序
    # 遍历目录，拼接出每个图片的【完整路径】并排序
    image_files = sorted([
        os.path.join(image_dir, f)  # 拼接目录和文件名，生成完整路径
        for f in os.listdir(image_dir) 
        if f.endswith('.jpeg')      # 过滤出.jpeg文件
    ])
    if not image_files:
        print("未找到任何JPEG图片！")
        return

    # 2. 按类别分组（利用sorted保证groupby生效）
    categorized = groupby(sorted(image_files, key=extract_category), key=extract_category)

    # 3. 初始化PDF画布
    c = canvas.Canvas(output_path, pagesize=page_size)
    page_w, page_h = page_size

    # 4. 遍历每个类别，生成对应页面
    for category, files in categorized:
        file_list = list(files)

        print(f"正在处理【{category}】有{len(file_list)}张图片")
        
        try:
            layout = calculate_layout(file_list, page_w, page_h, margin)
            draw_images(c, layout)
            draw_page_title(c, f"产品类别：{category}", page_w, page_h)
            c.showPage()  # 新建页面
        except Exception as e:
            print(f"处理类别 {category} 时出错：{e}")


    # 5. 保存PDF
    c.save()
    print(f"PDF已生成：{output_path}")


# ------------------- 测试运行 ------------------- #
if __name__ == "__main__":
    IMAGE_DIR = "/Users/teacher/Desktop/未命名文件夹/思凡尼2026图册_图片_副本"   # 替换为你的图片目录路径
    OUTPUT_PDF = "/Users/teacher/Desktop/未命名文件夹/output.pdf"  # 输出PDF路径
    PAGE_MARGIN = 10         # 页面边距（单位：点，1英寸=72点）

    generate_pdf(
        image_dir = IMAGE_DIR, 
        output_path = OUTPUT_PDF, 
        margin = PAGE_MARGIN
    )