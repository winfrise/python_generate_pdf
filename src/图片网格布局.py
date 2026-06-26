import os
from itertools import islice, chain
from functools import reduce
from reportlab.lib.pagesizes import A4, A3, landscape as RL_landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from PIL import Image as PILImage


# ==================== 1. 配置与工具层 (Configuration & Utils) ====================

def parse_page_size(size_input):
    """
    智能解析页面尺寸。
    支持: 'A4', 'A4-L' (横向), 或 [宽, 高] 列表 (单位 mm)。
    返回: (width_pt, height_pt)
    """
    if isinstance(size_input, str):
        size_map = {
            "A4": A4, 
            "A3": A3
        } # 可扩展
        base_size = size_map.get(size_input.upper(), A4)

        # 处理横向 (Landscape)
        if "-L" in size_input.upper():
            return (base_size[1], base_size[0])
        return base_size
    elif isinstance(size_input, (list, tuple)):
        # 假设输入是 mm，转换为 point (1mm = 2.8346pt)
        w, h = size_input
        return (w * mm, h * mm)
    else:
        raise ValueError(f"不支持的页面尺寸格式: {size_input}")


def get_image_paths(folder):
    """获取并排序图片路径 (纯函数)"""
    valid_ext = {'.jpg', '.jpeg', '.png', '.bmp'}
    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in valid_ext
    ]
    return sorted(files, key=os.path.basename)


# ==================== 2. 布局计算层 (Layout Calculation) ====================

def calculate_cell_layout(page_w, page_h, cols=2, rows=1, margin_x=20*mm, margin_y=20*mm, gap_x=10*mm, gap_y=10*mm):
    """
    根据页面尺寸和网格配置，计算每个格子的坐标和尺寸。
    返回: list of dicts [{'x':..., 'y':..., 'w':..., 'h':...}, ...]
    """
    # 计算可用区域
    usable_w = page_w - (2 * margin_x) - ((cols - 1) * gap_x)
    usable_h = page_h - (2 * margin_y) - ((rows - 1) * gap_y)

    cell_w = usable_w / cols
    cell_h = usable_h / rows

    # 生成所有格子的坐标信息
    cells = []
    for r in range(rows):
        for c in range(cols):
            x = margin_x + c * (cell_w + gap_x)
            y = page_h - margin_y - (r + 1) * cell_h - r * gap_y
            cells.append({'x': x, 'y': y, 'w': cell_w, 'h': cell_h})

    return cells


def fit_image_to_cell(img_path, cell_info):
    """
    计算图片在格子内的自适应尺寸和居中坐标。
    保持宽高比，不拉伸。
    """
    try:
        with PILImage.open(img_path) as img:
            img_w, img_h = img.size
    except Exception:
        return None # 无法读取的图片跳过

    cell_w, cell_h = cell_info['w'], cell_info['h']

    # 计算缩放比例 (取较小值以适应格子)
    ratio = min(cell_w / img_w, cell_h / img_h)
    final_w = img_w * ratio
    final_h = img_h * ratio

    # 计算居中偏移
    offset_x = (cell_w - final_w) / 2
    offset_y = (cell_h - final_h) / 2

    return {
        'path': img_path,
        'draw_x': cell_info['x'] + offset_x,
        'draw_y': cell_info['y'] + offset_y,
        'draw_w': final_w,
        'draw_h': final_h
    }


# ==================== 3. 数据处理层 (Data Processing) ====================

def chunk_list(lst, n):
    """将列表按大小 n 分块 (Generator)"""
    it = iter(lst)
    while True:
        chunk = tuple(islice(it, n))
        if not chunk:
            break
        yield chunk


def prepare_pages(image_paths, layout_config):
    """
    核心调度函数：将图片列表转换为“待绘制的页面数据”。
    返回: generator of pages, where each page is a list of draw instructions.
    """
    cols = layout_config['cols']
    rows = layout_config['rows']
    cells_per_page = cols * rows
    cells_template = layout_config['cells'] # 预计算的格子坐标

    # 1. 将图片分块
    image_chunks = chunk_list(image_paths, cells_per_page)

    # 2. 映射每一块图片到具体的绘图指令
    for chunk in image_chunks:
        # 对当前页的每一张图片，计算其绘图参数
        page_instructions = list(map(
            lambda pair: fit_image_to_cell(pair[0], pair[1]),
            zip(chunk, cells_template[:len(chunk)]) # 防止最后一张图越界
        ))
        # 过滤掉无法读取的图片
        yield [inst for inst in page_instructions if inst is not None]


# ==================== 4. 渲染执行层 (Rendering Execution) ====================

def render_pdf(output_path, pages_data, page_size):
    c = canvas.Canvas(output_path, pagesize=page_size)

    # --- 修改点 1: 使用 enumerate 获取页码 (从1开始) ---
    for page_num, page_instructions in enumerate(pages_data, start=1):
        
        # --- 修改点 2: 打印当前进度 ---
        print(f"正在生成第 {page_num} 页...") 

        for inst in page_instructions:
            c.drawImage(
                inst['path'],
                inst['draw_x'],
                inst['draw_y'],
                width=inst['draw_w'],
                height=inst['draw_h'],
                preserveAspectRatio=True,
                anchor='c'
            )
        c.showPage() # 结束当前页

    c.save()
    print("PDF 生成完毕！") 


# ==================== 5. 主入口 (Main Entry Point) ====================

def generate_grid_pdf(image_folder, output_pdf, page_size="A4", **layout_kwargs):
    """
    对外暴露的统一接口。
    组合了上述所有纯函数，形成完整的处理管道。
    """
    # 1. 解析配置
    p_w, p_h = parse_page_size(page_size)
    cells = calculate_cell_layout(p_w, p_h, **layout_kwargs)

    config = {
        'cols': layout_kwargs.get('cols', 2),
        'rows': layout_kwargs.get('rows', 1),
        'cells': cells
    }

    # 2. 获取数据
    images = get_image_paths(image_folder)

    # 3. 构建管道：Images -> Pages Data -> PDF File
    pages_stream = prepare_pages(images, config)
    render_pdf(output_pdf, pages_stream, (p_w, p_h))

    print(f"PDF 生成成功: {output_pdf} (共处理 {len(images)} 张图片)")


# --- 使用示例 ---
if __name__ == "__main__":

    image_folder="/Users/teacher/Desktop/未命名文件夹 3/思凡尼2026图册_图片_1"

    output_dir = "/Users/teacher/Desktop/未命名文件夹 3/"
    output_path = os.path.join(output_dir, "output.pdf")

    # 示例 1: 默认 A4, 2列1行
    # generate_grid_pdf(
    #     image_folder="./images",
    #     output_pdf="./output_a4.pdf",
    #     page_size="A4",
    #     cols=2,
    #     rows=2
    # )

    # 示例 2: 自定义尺寸 (宽300mm, 高200mm), 3列2行
    generate_grid_pdf(
        image_folder=image_folder,
        output_pdf=output_path,
        page_size=[300, 200],  # 传入列表表示自定义毫米尺寸
        cols=2,
        rows=2,
        margin_x=10, # 可以覆盖默认边距
        margin_y=10,
        gap_x=10*mm,
        gap_y=10*mm
    )