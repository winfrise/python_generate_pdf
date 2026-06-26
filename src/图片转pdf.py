
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, LETTER
from reportlab.lib.units import mm
from PIL import Image as PILImage
import os



PAGE_SIZE_MAP = {
    'a4': A4,       # (595.27, 841.89)
    'a3': A3,       # (841.89, 1190.55)
    'letter': LETTER,
    # 你也可以在这里添加更多预设
}

def image_to_pdf(output_path, image_folder, page_size):
    print(f"正在使用 ReportLab 生成新 PDF...")

    def _get_page_size(page_size):
        target_size = None
        
        if isinstance(page_size, str):
            # 如果是字符串，去 Map 里找，找不到默认用 A4
            target_size = PAGE_SIZE_MAP.get(page_size.lower(), A4)
            print(f"检测到字符串尺寸 '{page_size}'，已匹配为: {target_size}")
        elif isinstance(page_size, (tuple, list)) and len(page_size) == 2:
            # 如果是元组或列表，直接使用
            target_size = tuple(page_size)
            print(f"检测到自定义尺寸: {target_size}")
        else:
            # 兜底处理
            target_size = A4
            print(f"无效的尺寸格式，已回退到默认 A4")
        
        print(target_size)
        return target_size

    def _get_image(folder):
        """获取并排序图片路径 (纯函数)"""
        valid_ext = {'.jpg', '.jpeg', '.png', '.bmp'}
        files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in valid_ext
        ]
        return sorted(files, key=os.path.basename)

    
    # 1. 获取 A4 纸尺寸 (单位：点 pt)
    page_w, page_h = _get_page_size(page_size=page_size) 
    
    c = canvas.Canvas(output_path, pagesize=(page_w, page_h))
    
    images = _get_image(image_folder)

    for image_index in range(len(images)):
        print(f"正在插入第 {image_index + 1} 张图片...") 
        image_path =  images[image_index]
        # 2. 获取图片原始像素尺寸
        img = PILImage.open(image_path)
        img_w, img_h = img.size 
        
        # 3. 核心：计算合适的缩放比率，确保图片完整显示在 A4 内且不变形
        ratio = min(page_w / img_w, page_h / img_h)
        target_width_pt = img_w * ratio
        target_height_pt = img_h * ratio
        
        
        # 计算居中坐标 (ReportLab 的坐标系原点在左下角)
        center_x = (page_w - target_width_pt) / 2
        center_y = (page_h - target_height_pt) / 2
        
        c.drawImage(
            image_path, 
            center_x, center_y, 
            width=target_width_pt, 
            height=target_height_pt, 
            preserveAspectRatio=True, 
            mask='auto'
        )

        c.showPage()
    
    c.save()
    print(f"    -> 生成成功！物理尺寸: {target_width_pt:.2f}pt x {target_height_pt:.2f}pt")


# ================= 执行主流程 =================
if __name__ == "__main__":
        output_path = "/Users/teacher/Desktop/未命名文件夹 3/111.pdf"
        image_folder = "/Users/teacher/Desktop/未命名文件夹 3/思凡尼2026图册_图片_1"
        page_size = "A3"
        image_to_pdf(
             output_path=output_path,
             image_folder=image_folder,
             page_size=page_size
        )