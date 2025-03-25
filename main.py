import os
import time
import yaml
from PIL import Image
from PyPDF2 import PdfWriter
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import jmcomic
import re
import zipfile
import random
import string

def natural_sort_key(s):
    """实现自然排序的key函数"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def process_image(image_path, resolution):
    """处理单张图片并返回PDF页面的BytesIO对象"""
    with Image.open(image_path) as img:
        img_pdf_bytes = BytesIO()
        img.save(img_pdf_bytes, "PDF", resolution=resolution)  # 调整分辨率以优化速度
        img_pdf_bytes.seek(0)  # 将指针重置到文件开头
        return img_pdf_bytes

def images_to_pdf_parallel(image_paths, output_pdf_path, resolution, max_workers=4):
    """将多张图片并行转换为PDF，并保证顺序正确"""
    pdf_writer = PdfWriter()
    
    # 使用线程池并行处理图片
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有图片处理任务，并按顺序保存Future对象
        futures = [executor.submit(process_image, path, resolution) for path in image_paths]
        
        # 按顺序获取结果并追加到PDF
        for future in futures:
            try:
                img_pdf_bytes = future.result()
                pdf_writer.append(img_pdf_bytes)
            except Exception as e:
                print(f"处理图片时出错: {e}")

    # 保存最终的PDF文件
    with open(output_pdf_path, "wb") as output_pdf_file:
        pdf_writer.write(output_pdf_file)

    print(f"PDF已保存至: {output_pdf_path}")

def generate_random_password(length=12):
    """生成随机密码"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

def compress_with_password(file_path, delete_original=True):
    """将文件压缩为加密ZIP"""
    # 生成随机密码
    password = generate_random_password()
    
    # 创建ZIP文件路径
    zip_path = file_path + '.zip'
    
    # 创建加密ZIP文件
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 设置密码
        zipf.setpassword(password.encode())
        # 添加文件到ZIP
        zipf.write(file_path, os.path.basename(file_path))
    
    # 如果需要删除原文件
    if delete_original and os.path.exists(zip_path):
        os.remove(file_path)
    
    print(f"文件已加密压缩，保存为：{zip_path}")
    print(f"解压密码：{password}")
    
    return zip_path, password

def all2PDF(input_folder, pdfpath, pdfname, max_workers=4, need_compress=False, resolution=100):
    """将文件夹中的图片转换为PDF，支持多线程并行处理"""
    start_time = time.time()
    
    # 获取所有图片路径
    image_paths = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                image_paths.append(os.path.join(root, file))
    
    # 使用自然排序，确保按照数字顺序正确排序
    image_paths.sort(key=natural_sort_key)

    # 生成PDF文件路径
    if not pdfname.endswith(".pdf"):
        pdfname += ".pdf"
    pdf_file_path = os.path.join(pdfpath, pdfname)

    # 调用多线程函数生成PDF
    images_to_pdf_parallel(image_paths, pdf_file_path, max_workers=max_workers, resolution=resolution)
    
    # 如果需要加密压缩
    if need_compress:
        compress_with_password(pdf_file_path)

    # 计算运行时间
    end_time = time.time()
    run_time = end_time - start_time
    print(f"运行时间：{run_time:.2f} 秒")

def download_and_convert(album_ids, config_path, max_workers=4, need_compress=False, resolution="mid"):
    """下载漫画并转换为PDF"""
    # 加载配置文件
    loadConfig = jmcomic.JmOption.from_file(config_path)
    base_dir = loadConfig.dir_rule.base_dir  # 漫画下载目录

    resolution_list = {"very_low":70, "low": 100, "mid": 150,"high": 200, "very_high": 300}
    resolution = resolution_list[resolution]

    # 下载漫画
    for album_id in album_ids:
        print(f"开始下载漫画：{album_id}")
        jmcomic.download_album(album_id, loadConfig)

    # 遍历目录，将每个子目录转换为PDF
    with os.scandir(base_dir) as entries:
        for entry in entries:
            if entry.is_dir():
                pdf_name = entry.name + ".pdf"
                pdf_path = os.path.join(base_dir, pdf_name)
                zip_path = pdf_path + '.zip'
                
                if os.path.exists(zip_path):
                    print(f"文件：《{entry.name}》 已存在，跳过")
                    continue
                else:
                    print(f"开始转换：{entry.name}")
                    all2PDF(entry.path, base_dir, entry.name, max_workers=max_workers, need_compress=need_compress)

if __name__ == "__main__":
    # 自定义设置
    config_path = "config.yml"  # 配置文件路径
    album_ids = ['422866']  # 需要下载的漫画ID列表
    max_workers = 8  # 线程数
    need_compress = False  # 是否需要加密压缩
    resolution = "very_high" # PDF质量

    # 下载并转换漫画
    download_and_convert(album_ids, config_path, max_workers=max_workers, need_compress=need_compress, resolution=resolution)