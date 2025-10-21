import os
import shutil
import time
import logging
import re
import csv
from logging.handlers import TimedRotatingFileHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pandas as pd
import xlrd
from collections import defaultdict


import fitz  # PyMuPDF

def convert_pdf_to_images(pdf_path):
    """使用PyMuPDF将PDF的每一页转换为PIL Image对象"""
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # 设置缩放比例，提高图像质量以利于OCR
        zoom_x = 2.0
        zoom_y = 2.0
        mat = fitz.Matrix(zoom_x, zoom_y)
        pix = page.get_pixmap(matrix=mat)

        # 转换为PIL Image
        from PIL import Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images

# 2. 使用PaddleOCR识别图像中的文本
from paddleocr import PaddleOCR

# 初始化OCR引擎，仅需运行一次
# lang='ch' 表示识别中文
ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

def ocr_invoice_image(image_list):
    """对图像列表进行OCR识别，并返回结构化结果"""
    full_ocr_result = []
    for img in image_list:
        # PaddleOCR接受 numpy array 或 image path
        result = ocr.ocr(img, det=True, cls=True)
        
        # 提取文本结果
        page_text = []
        for line in result:
            if line:
                # line[1][0] 是识别到的文本
                page_text.append(line[1][0])
        full_ocr_result.extend(page_text)
        
    # 将所有行合并成一个大字符串，方便后续正则表达式处理
    return "\n".join(full_ocr_result)

# 示例流程：

# 示例：
path = "C:\ds_projects\invoice_detection\Src\data\source\invoice.pdf"
images = convert_pdf_to_images(path)
# ocr_text = ocr_invoice_image(images)
# print(ocr_text)





# MOUNT_POINT = r"C:\\ds_projects\\invoice_detection\\Src\\data"
# SOURCE_DIR = os.path.join(MOUNT_POINT, 'source')
# OUTPUT_DIR = os.path.join(MOUNT_POINT, 'output')
# PROCESSED_DIR = os.path.join(MOUNT_POINT, 'processed')

# APP_DIR = os.path.dirname(os.path.abspath(__file__))
# ERROR_DIR = os.path.join(APP_DIR, 'error')
# LOG_FILE = os.path.join(APP_DIR, "file_processor.log")
# # --- End Configuration ---



# def setup_logging():
#     """Configures rotating logging to keep 3 days of logs."""
#     logger = logging.getLogger()
#     logger.setLevel(logging.INFO)

#     # Clear existing handlers to prevent duplicate logs from being created
#     if logger.hasHandlers():
#         logger.handlers.clear()

#     formatter = logging.Formatter(
#         "%(asctime)s - [%(levelname)s] - %(message)s")

#     file_handler = TimedRotatingFileHandler(
#         LOG_FILE,
#         when="midnight",
#         interval=1,
#         backupCount=3,
#         encoding='utf-8'
#     )
#     file_handler.setFormatter(formatter)

#     stream_handler = logging.StreamHandler()
#     stream_handler.setFormatter(formatter)

#     logger.addHandler(file_handler)
#     logger.addHandler(stream_handler)


# def process_bgs_file(file_path, filename):
#     """
#     Processes Excel files starting with 'BGS' by parsing thickness data.
#     """
#     logging.info(f"Using BGS processor for {filename}")


#     # 0. import format file
#     sample_file = SAMPLE_DIR + '\BGS_BGD_sample.csv'
#     sample_pd = pd.read_csv(sample_file)
#     data_pd = sample_pd
#     data_pd.fillna('',inplace=True)


#     # 1. Read the Excel file into a pandas DataFrame
#     df = pd.read_excel(xlrd.open_workbook(file_path,encoding_override='gbk')) 

#     # 2. Find the relevant data section ("研磨厚度")
#     section_title_str = "研磨厚度"
#     section_start_row = -1
#     for i, row in df.iterrows():
#         # Check if the section title is in the first cell of the row
#         if isinstance(row.iloc[0], str) and section_title_str in row.iloc[0]:
#             section_start_row = i
#             break

#     if section_start_row == -1:
#         raise ValueError(
#             f"Section '{section_title_str}' not found in {filename}")


#     # 3. Extract data from the located section
#     # The header is the row after the section title, and data is the row after that
#     header_row = df.iloc[section_start_row + 1]
#     data_row = df.iloc[section_start_row + 2]
#     # Create a map from header name to column index, skipping empty/invalid headers
#     header_map = {str(name).strip(): i for i, name in header_row.items(
#     ) if pd.notna(name) and str(name).strip()}

#     # Extract metadata using the header map
#     lot_id = data_row.get(header_map.get('客户批号'))
#     operator = data_row.get(header_map.get('检验人员'))
#     tool_name = data_row.get(header_map.get('生产机台'))
#     product_name = data_row.get(header_map.get('产品名称'))

#     # Derive values from extracted data
#     step_name = "WAFER_THINNING"
#     full_section_title = df.iloc[section_start_row, 0]
#     golden_sample_match = re.search(r'\((\d+)', full_section_title)
#     golden_sample = f"WAFER_THICKNESS:{golden_sample_match.group(1)}" if golden_sample_match else "N/A"

#     design_id_match = re.search(r'\((.*?)\)', str(product_name))
#     design_id = design_id_match.group(1) if design_id_match else "N/A"


#     data_pd.loc[data_pd['index']=='LOT_ID', 'value'] = lot_id
#     data_pd.loc[data_pd['index']=='PROCESS_TOOL_NAME', 'value'] = tool_name
#     data_pd.loc[data_pd['index']=='GOLDEN_SAMPLE', 'value'] = golden_sample
#     data_pd.loc[data_pd['index']=='DESIGN_ID', 'value'] = design_id


#     # 4. Find and collect the numeric thickness values
#     # This robust method explicitly finds columns named like '1-1', '1-2', etc.,
#     # and sorts them to guarantee the correct order.
#     wafer_thk_values = {
#         'WAFER_THK':section_start_row + 2,
#         'WAFER_RNG':section_start_row + 2 + 4*1,
#     }

#     for item,data_row_index in wafer_thk_values.items(): 
#         data_row_temp = df.iloc[data_row_index]
        
#         for header_name, col_index in header_map.items():
#             if re.match(r'^\d+-\d+$', header_name):
#                 value = data_row_temp.get(col_index)
#                 if pd.notna(value):
#                     index_value = item + ' '+ header_name
#                     data_pd.loc[data_pd['index'] == index_value, 'value'] = value
    

#     data_pd.drop(columns=['index'],inplace=True)
#     output_filename = filename.replace('.xlsx','.csv').replace('.xls','.csv')
#     output_path = os.path.join(OUTPUT_DIR, output_filename)
#     data_pd.to_csv(output_path,index=False,header=False)


#     logging.info(
#         f"Successfully processed {filename}, result saved to {output_path}")


# def process_ssh_file(file_path, filename):

#     # 1. Check for Excel file extension
#     if not filename.lower().endswith(('.xlsx', '.xls')):
#         # This is a BGS file, but not in the expected Excel format. Treat as an error.
#         raise ValueError("SSH file is not an Excel file.")
    
#     sample_file = SAMPLE_DIR + '\SSH_sample.csv'
#     sample_pd = pd.read_csv(sample_file)
#     data_pd = sample_pd
#     data_pd.fillna('',inplace=True)


#     """
#     Processes Excel files starting with 'SSH' by parsing thickness data.
#     """
#     logging.info(f"Using SSH processor for {filename}")


#     # 1. Check for Excel file extension
#     if not filename.lower().endswith(('.xlsx', '.xls')):
#         # This is a BGS file, but not in the expected Excel format. Treat as an error.
#         raise ValueError("SSH file is not an Excel file.")
    

#     # 2. Read the Excel file into a pandas DataFrame
#     df = pd.read_excel(file_path, header=None, engine='openpyxl')


#     # 3. Find the relevant data section ("平坦度")
#     section_title_str = "平坦度"
#     section_start_row = -1
#     for i, row in df.iterrows():
#         # Check if the section title is in the first cell of the row
#         if isinstance(row.iloc[0], str) and section_title_str in row.iloc[0]:
#             section_start_row = i
#             break

#     if section_start_row == -1:
#         raise ValueError(
#             f"Section '{section_title_str}' not found in {filename}")
    

#     # 4. Extract data from the located section
#     # The header is the row after the section title, and data is the row after that
#     header_row = df.iloc[section_start_row + 1]
#     data_row = df.iloc[section_start_row + 2]
#     # Create a map from header name to column index, skipping empty/invalid headers
#     header_map = {str(name).strip(): i for i, name in header_row.items(
#     ) if pd.notna(name) and str(name).strip()}


#     # Extract metadata using the header map
#     lot_id = data_row.get(header_map.get('检测批号'))
#     operator = data_row.get(header_map.get('检验人员'))
#     tool_name = data_row.get(header_map.get('生产机台'))


#     product_name = df.iloc[section_start_row + 6].get(header_map.get('产品名称'))
#     design_id_match = re.search(r'\((.*?)\)', str(product_name))
#     design_id = design_id_match.group(1) if design_id_match else "N/A"


#     # Derive values from extracted data
#     step_name = "封装尺寸-X"
#     full_section_title = df.iloc[section_start_row + 4, 0]
#     package_match = re.search(r'\((\d*\.?\d+X\d+)', full_section_title)
#     package_width = f"{package_match.group(1).split('X')[0]}" if package_match else "N/A"
#     package_length = f"{package_match.group(1).split('X')[1]}" if package_match else "N/A"


#     data_pd.loc[data_pd['index']=='LOT_ID', 'value'] = lot_id
#     data_pd.loc[data_pd['index']=='OPERATOR', 'value'] = operator
#     data_pd.loc[data_pd['index']=='PROCESS_TOOL_NAME', 'value'] = tool_name

#     data_pd.loc[data_pd['index']=='PACKAGE_LENGTH', 'value'] = package_length
#     data_pd.loc[data_pd['index']=='PACKAGE_WIDTH', 'value'] = package_width
#     data_pd.loc[data_pd['index']=='DESIGN_ID', 'value'] = design_id


#     # # 5. Find and collect the numeric thickness values
#     # This robust method explicitly finds columns named like '1-1', '1-2', etc.,
#     # and sorts them to guarantee the correct order.
#     wafer_thk_values = {

#         'COP_SPCDL':section_start_row + 2,
#         'WIDTH_PKG_LOT_SPCDL':section_start_row + 2 + 4*1,
#         'LENGTH_PKG_LOT_SPCDL':section_start_row + 2 + 4*2,
#         'STANDOFF_SPCDL':section_start_row + 2 + 4*3,
#         'BALLDIA_SPCDL':section_start_row + 2 + 4*4,
#         'OFFSET_X_SPCDL':section_start_row + 2 + 4*5,
#         'OFFSET_Y_SPCDL':section_start_row + 2 + 4*6,
#         'WARPAGE_SPCDL':section_start_row + 2 + 4*7,

#     }

#     # Iterate through all headers to find ones that match the measurement pattern (e.g., '1-1')
#     for item,data_row_index in wafer_thk_values.items(): 
#         data_row_temp = df.iloc[data_row_index]
        
#         for header_name, col_index in header_map.items():
#             if re.match(r'^\d+-\d+$', header_name):
#                 value = data_row_temp.get(col_index)
#                 if pd.notna(value):
#                     index_value = item + ' '+ header_name
#                     data_pd.loc[data_pd['index'] == index_value, 'value'] = value
    

#     data_pd.drop(columns=['index'],inplace=True)
#     output_filename = filename.replace('.xlsx','.csv').replace('.xls','.csv')
#     output_path = os.path.join(OUTPUT_DIR, output_filename)
#     data_pd.to_csv(output_path,index=False,header=False)


#     logging.info(
#         f"Successfully processed {filename}, result saved to {output_path}")



# def process_dcd_group(group_name, file_paths):
#     """
#     处理 DCD 文件分组。

#     Args:
#         group_name (str): 分组的标识符（例如 "DCD012_25X904297.00"）。
#         file_paths (list): 属于该分组的文件路径列表。
#     """
#     logging.info(f"Processing DCD group: {group_name} with files: {', '.join(os.path.basename(p) for p in file_paths)}")
#     group_name = group_name.split('.')[0]


#     sample_file = SAMPLE_DIR + '\DCD_sample.csv'
#     sample_pd = pd.read_csv(sample_file)
#     data_pd = sample_pd
#     data_pd.fillna('',inplace=True)


#     for file_path_item in file_paths:

#         # 1. Check for Excel file extension
#         if not file_path_item.lower().endswith(('.xlsx', '.xls')):
#             # This is a BGS file, but not in the expected Excel format. Treat as an error.
#             raise ValueError("DCD file is not an Excel file.")
        

#         # 2. Read the Excel file into a pandas DataFrame
#         if file_path_item.lower().endswith('.xlsx'):
#             # 使用 openpyxl 处理 .xlsx 文件
#             df = pd.read_excel(file_path_item, engine='openpyxl')
        
#         elif file_path_item.lower().endswith('.xls'):
#             # 使用 xlrd 处理 .xls 文件
#             # 确保你已经 pip install xlrd
#             df = pd.read_excel(xlrd.open_workbook(file_path_item,encoding_override='gbk')) 
            
#         else:
#             logging.warning(f"Skipping unsupported file type for read")
#             continue # 跳过不支持的文件类型

        
#         section_title_str_0 = "正面剥离(崩缺)"
#         section_title_str_1 = "中心偏移量-S1"
#         section_start_row = -1
#         file_index = -1
#         for i, row in df.iterrows():
#             # Check if the section title is in the first cell of the row
#             if isinstance(row.iloc[0], str):
#                 if row.iloc[0] in [section_title_str_0,section_title_str_1]:
#                     section_start_row = i

#                     if section_title_str_0 in row.iloc[0]:

#                         file_index = 0
#                         wafer_thk_values = {
#                             'KERF_PEELING':section_start_row + 2
#                         }
                    
#                     if section_title_str_1 in row.iloc[0]:
                        
#                         file_index = 1
#                         wafer_thk_values = {
#                             'KERF_OFFSITE_S1':section_start_row + 2,
#                             'KERF_OFFSITE_S2':section_start_row + 2 + 4*1,
#                             'KERF_WIDTH_F1_S1':section_start_row + 2 + 4*2,
#                             'KERF_WIDTH_F1_S2':section_start_row + 2 + 4*3,
#                             'KERF_WIDTH_S1':section_start_row + 2 + 4*4,
#                             'KERF_WIDTH_S2':section_start_row + 2 + 4*5,
#                         }
                        
#                     break
        

#         if section_start_row == -1:
#             raise ValueError(
#                 f"Section '{section_title_str_0}' or '{section_title_str_1}' not found in {file_path_item}")
        

#         # 4. Extract data from the located section
#         # The header is the row after the section title, and data is the row after that
#         header_row = df.iloc[section_start_row + 1]
#         data_row = df.iloc[section_start_row + 2]
#         # Create a map from header name to column index, skipping empty/invalid headers
#         header_map = {str(name).strip(): i for i, name in header_row.items(
#         ) if pd.notna(name) and str(name).strip()}


#         if file_index == 0 or (data_pd.loc[data_pd['name']=='PROCESS_TOOL_NAME', 'value'] != 0).any():

#             # Extract metadata using the header map
#             lot_id = data_row.get(header_map.get('检测批号'))
#             tool_name = data_row.get(header_map.get('生产机台'))

#             data_pd.loc[data_pd['index']=='PROCESS_TOOL_NAME', 'value'] = tool_name
#             data_pd.loc[data_pd['index']=='LOT_ID', 'value'] = lot_id

#         else:

#             product_name = df.iloc[section_start_row + 18].get(header_map.get('产品名称'))
#             design_id_match = re.search(r".*\(([^)]+)\).*", str(product_name))
#             design_id = design_id_match.group(1) if design_id_match else "N/A"
#             data_pd.loc[data_pd['index']=='DESIGN_ID', 'value'] = design_id


#         # 5. Find and collect the numeric thickness values
#         # This robust method explicitly finds columns named like '1-1', '1-2', etc.,
#         # and sorts them to guarantee the correct order.

#         # 中心偏移量-S1：KERF_OFFSITE_S1, 
#         # 中心偏移量-S2：KERF_OFFSITE_S2, 
#         # 切割宽度(F1)-S1-Kerf BB: KERF_WIDTH_F1_S1, 
#         # 切割宽度(F1)-S2-Kerf BB: KERF_WIDTH_F1_S2，
#         # Kerf Width-S1-Kerf BB：KERF_WIDTH_S1, 
#         # Kerf Width-S2-Kerf BB：KERF_WIDTH_S2，
#         # 正面剥离（崩缺）：KERF_PEELING

#         # Iterate through all headers to find ones that match the measurement pattern (e.g., '1-1')
#         for item,data_row_index in wafer_thk_values.items(): 
#             data_row_temp = df.iloc[data_row_index]
            
#             for header_name, col_index in header_map.items():
#                 if re.match(r'^\d+-\d+$', header_name):
#                     value = data_row_temp.get(col_index)

#                     if pd.notna(value) and value != '-9999':
#                         index_value = item + ' '+ header_name
#                         data_pd.loc[data_pd['index'] == index_value, 'value'] = value
    
    
#     data_pd.drop(columns=['index'],inplace=True)
#     output_filename = group_name +'.csv'
#     output_path = os.path.join(OUTPUT_DIR, output_filename)
#     data_pd.to_csv(output_path,index=False,header=False)
    
#     logging.info(
#         f"Successfully processed {group_name}, result saved to {output_path}")


# def process_mke_group(group_name, file_paths):

#     """
#     处理 MKE 文件分组。

#     Args:
#         group_name (str): 分组的标识符（例如 "MKE031_202509150338"）。
#         file_paths (list): 属于该分组的文件路径列表。
#     """
#     logging.info(f"Processing MKE group: {group_name} with files: {', '.join(os.path.basename(p) for p in file_paths)}")


#     sample_file = SAMPLE_DIR + '\MKE_sample.csv'
#     sample_pd = pd.read_csv(sample_file)
#     data_pd = sample_pd
#     data_pd.fillna('',inplace=True)


#     for file_path_item in file_paths:

#         # 1. Check for Excel file extension
#         if not file_path_item.lower().endswith(('.xlsx', '.xls')):
#             # This is a BGS file, but not in the expected Excel format. Treat as an error.
#             raise ValueError("DCD file is not an Excel file.")
        

#         # 2. Read the Excel file into a pandas DataFrame
#         if file_path_item.lower().endswith('.xlsx'):
#             # 使用 openpyxl 处理 .xlsx 文件
#             df = pd.read_excel(file_path_item, engine='openpyxl')
        
#         elif file_path_item.lower().endswith('.xls'):
#             # 使用 xlrd 处理 .xls 文件
#             # 确保你已经 pip install xlrd
#             df = pd.read_excel(xlrd.open_workbook(file_path_item,encoding_override='gbk')) 
            
#         else:
#             logging.warning(f"Skipping unsupported file type for read")
#             continue # 跳过不支持的文件类型

        
#         section_title_str_0 = "镭射深度"
#         section_title_str_1 = "2DID盖印深度"
#         section_title_str_2 = "2DID盖印等级"
#         section_title_str_3 = "镭射深度(字码)"

#         section_start_row = -1
#         file_index = -1


#         for i, row in df.iterrows():
#             # Check if the section title is in the first cell of the row
#             if isinstance(row.iloc[0], str):
#                 if row.iloc[0] in [section_title_str_0,section_title_str_1,section_title_str_2,section_title_str_3]:
#                     section_start_row = i

#                     if section_title_str_0 == row.iloc[0]:

#                         file_index = 0
#                         wafer_thk_values = {
#                             'LASER_DEPTH':section_start_row + 2
#                         }
                    
#                     if section_title_str_1 == row.iloc[0]:
                        
#                         file_index = 1
#                         wafer_thk_values = {
#                             '2D_DEPTH':section_start_row + 2,
#                         }

#                     if section_title_str_2 == row.iloc[0]:
                        
#                         file_index = 2
#                         wafer_thk_values = {
#                             '2D_GRADE':section_start_row + 2,
#                         }
                    
#                     if section_title_str_3 == row.iloc[0]:
                        
#                         file_index = 3
#                         wafer_thk_values = {
#                             'LASER_CODE_DEPTH':section_start_row + 2,
#                         }
                        
#                     break
        

#         if section_start_row == -1:
#             raise ValueError(
#                 f"Section '{section_title_str_1}' or '{section_title_str_2}' not found in {file_path_item}")
        

#         # 4. Extract data from the located section
#         # The header is the row after the section title, and data is the row after that
#         header_row = df.iloc[section_start_row + 1]
#         data_row = df.iloc[section_start_row + 2]
#         # Create a map from header name to column index, skipping empty/invalid headers
#         header_map = {str(name).strip(): i for i, name in header_row.items(
#         ) if pd.notna(name) and str(name).strip()}


#         if file_index == 0 or (data_pd.loc[data_pd['name']=='PROCESS_TOOL_NAME', 'value'] != 0).any():

#             # Extract metadata using the header map
#             lot_id = data_row.get(header_map.get('检测批号'))
#             tool_name = data_row.get(header_map.get('生产机台'))

#             product_name = data_row.get(header_map.get('产品型号'))
#             design_id_match = re.search(r"^([0-9A-Za-z]{4})", str(product_name))
#             design_id = design_id_match.group(1) if design_id_match else "N/A"

#             data_pd.loc[data_pd['index']=='PROCESS_TOOL_NAME', 'value'] = tool_name
#             data_pd.loc[data_pd['index']=='LOT_ID', 'value'] = lot_id
#             data_pd.loc[data_pd['index']=='DESIGN_ID', 'value'] = design_id


#         # 5. Find and collect the numeric thickness values
#         # This robust method explicitly finds columns named like '1-1', '1-2', etc.,
#         # and sorts them to guarantee the correct order.

#         # 镭射深度：LASER_DEPTH, 
#         # 2DID盖印深度：2D_DEPTH, 
#         # 2DID盖印等级：2D_GRADE, 
#         # 镭射深度（字码）：LASER_CODE_DEPTH
 

#         # Iterate through all headers to find ones that match the measurement pattern (e.g., '1-1')
#         for item,data_row_index in wafer_thk_values.items(): 
#             data_row_temp = df.iloc[data_row_index]
#             # print('data_row_temp:',data_row_temp)
            
#             for header_name, col_index in header_map.items():
#                 if re.match(r'^\d+-\d+$', header_name):
#                     value = data_row_temp.get(col_index)
                    
#                     if pd.notna(value):
#                         index_value = item + ' '+ header_name
#                         data_pd.loc[data_pd['index'] == index_value, 'value'] = value
    
    
#     data_pd.drop(columns=['index'],inplace=True)
#     output_filename = group_name +'.csv'
#     output_path = os.path.join(OUTPUT_DIR, output_filename)
#     data_pd.to_csv(output_path,index=False,header=False)

    
#     logging.info(
#         f"Successfully processed {group_name}, result saved to {output_path}")



# def get_dcd_group_key(filename):
#     """
#     从 DCD 文件名中提取用于分组的键。
#     例如: "DCD012_25X904297.00_202509170359_A31.xlsx" -> "DCD012_25X904297.00"

#     Args:
#         filename (str): 文件名。

#     Returns:
#         str: 用于分组的键，如果不是 DCD 文件则返回 None。
#     """
#     parts = filename.split('_')
#     if len(parts) >= 3 and parts[0].startswith('DCD'):
#         # 假设分组的标识是前两个下划线分隔的部分
#         return "_".join(parts[:2])
#     return None


# def get_mke_group_key(filename):
#     """
#     从 MKE 文件名中提取用于分组的键。
#     例如: "MKE031_20250915033805" -> "MKE031_202509150338"
#     """
#     parts = filename.split('_')
#     if len(parts) >= 2 and parts[0].startswith('MKE'):
#         # 提取第一个下划线以及下一个下划线之前的部分
#         # 假设格式是 MKE..._YYYYMMDDHHMMSS
#         # 我们需要 MKE..._YYYYMMDDHHMM
#         try:
#             base_part = "_".join(parts[:1]) # MKE031
#             datetime_part = parts[1] # 20250915033805
#             if len(datetime_part) >= 12:
#                 return f"{base_part}_{datetime_part[:12]}" # MKE031_202509150338
#         except IndexError:
#             pass # 避免列表索引错误
#     return None



# def process_directory_files(directory_path):
#     """
#     从指定目录中收集文件，根据文件名进行分组（DCD, MKE），
#     然后分发给相应的处理器，并处理文件的移动。

#     Args:
#         directory_path (str): 包含待处理文件的目录路径。
#     """

#     print('11:',directory_path)
#     if not os.path.isdir(directory_path):
#         logging.error(f"Directory not found: {directory_path}")
#         return

#     # 收集文件，并为 DCD 和 MKE 文件准备分组
#     dcd_groups = defaultdict(list)
#     mke_groups = defaultdict(list)
#     other_files_to_process = [] # 用于存放需要单独处理的 BGS, SSH, 未分组 MKE 等文件

#     logging.info(f"Scanning directory: {directory_path}")

#     for filename in os.listdir(directory_path):
#         file_path = os.path.join(directory_path, filename)
#         print('file path:',file_path)

#         if not os.path.isfile(file_path):
#             continue # 跳过目录

#         # 1. 处理 DCD 文件分组
#         if filename.lower().startswith('dcd'):
#             group_key = get_dcd_group_key(filename)
#             if group_key:
#                 dcd_groups[group_key].append(file_path)
#                 # logging.debug(f"  - Assigned to DCD group: {group_name}")
#             else:
#                 logging.warning(f"Could not determine DCD group key. Treating as other file.")
#                 other_files_to_process.append((file_path, filename)) # 无法分组的 DCD 文件按其他文件处理

#         # 2. 处理 MKE 文件分组
#         elif filename.lower().startswith('mke'):
#             group_key = get_mke_group_key(filename)
#             if group_key:
#                 mke_groups[group_key].append(file_path)
#                 # logging.debug(f"  - Assigned to MKE group: {group_name}")
#             else:
#                 logging.warning(f"Could not determine MKE group key for, Treating as other file.")
#                 other_files_to_process.append((file_path, filename)) # 无法分组的 MKE 文件按其他文件处理

#         # 3. 处理其他类型的文件 (BGS, SSH, 以及其他未匹配到的)
#         else:
#             other_files_to_process.append((file_path, filename))

    
    
#     # --- 开始处理分组和单个文件 ---
#     # 处理 DCD 文件分组
#     print('dcd_groups:',dcd_groups)
#     for group_name, file_paths in dcd_groups.items():
#         print('group_name and file_paths:',group_name,file_paths)
#         try:
#             process_dcd_group(group_name, file_paths)
#             # 成功处理后，将分组中的所有文件移动到 PROCESSED_DIR
#             for file_path in file_paths:
#                 try:
#                     processed_path = os.path.join(PROCESSED_DIR, os.path.basename(file_path))
#                     shutil.move(file_path, processed_path)
#                     logging.info(f"Moved DCD file '{os.path.basename(file_path)}' from group '{group_name}' to:")
#                 except Exception as move_e:
#                     logging.error(f"Error moving DCD file '{os.path.basename(file_path)}' to processed folder:")
#         except Exception as e:
#             logging.error(f"Error processing DCD group '{group_name}'")
#             # 如果处理分组时出错，将该分组中的所有文件移动到 ERROR_DIR
#             for file_path in file_paths:
#                 try:
#                     error_path = os.path.join(ERROR_DIR, os.path.basename(file_path))
#                     shutil.move(file_path, error_path)
#                     logging.info(f"Moved failed DCD file '{os.path.basename(file_path)}' from group '{group_name}' to error folder")
#                 except Exception as move_e:
#                     logging.error(
#                         f"Could not move failed DCD file '{os.path.basename(file_path)}' from group '{group_name}' to error folder")

    
#     # 处理 MKE 文件分组
#     for group_name, file_paths in mke_groups.items():
#         try:
#             # 调用新的分组处理函数 process_mke_group
#             process_mke_group(group_name, file_paths)
#             # 成功处理后，将分组中的所有文件移动到 PROCESSED_DIR
#             for file_path in file_paths:
#                 try:
#                     processed_path = os.path.join(PROCESSED_DIR, os.path.basename(file_path))
#                     shutil.move(file_path, processed_path)
#                     logging.info(f"Moved MKE file '{os.path.basename(file_path)}' from group '{group_name}' to")
#                 except Exception as move_e:
#                     logging.error(f"Error moving MKE file '{os.path.basename(file_path)}' to processed folder")
#         except Exception as e:
#             logging.error(f"Error processing MKE group '{group_name}'")
#             # 如果处理分组时出错，将该分组中的所有文件移动到 ERROR_DIR
#             for file_path in file_paths:
#                 try:
#                     error_path = os.path.join(ERROR_DIR, os.path.basename(file_path))
#                     shutil.move(file_path, error_path)
#                     logging.info(f"Moved failed MKE file '{os.path.basename(file_path)}' from group '{group_name}' to error folder")
#                 except Exception as move_e:
#                     logging.error(
#                         f"Could not move failed MKE file '{os.path.basename(file_path)}' from group '{group_name}' to error folder")

#     # 处理其他单个文件 (BGS, SSH, 未分组 DCD/MKE, 和其他类型)
#     for file_path, filename in other_files_to_process:
#         print('here for other:',file_path,filename)
#         # 再次检查文件是否存在，因为可能在分组处理中已被移动或删除
#         if not os.path.exists(file_path):
#             logging.warning(f"File no longer exists, skipping for individual processing.")
#             continue

#         try:
#             if filename.lower().startswith('bgs') or filename.lower().startswith('bgd'):
#                 process_bgs_file(file_path, filename)
#             elif filename.lower().startswith('ssh'):
#                 process_ssh_file(file_path, filename)
#             # MKE 文件在这里不会再被处理，因为它们已经被分组处理过了 (除非它们是未能分组的 MKE 文件)
#             # DCD 文件在这里也不会再被处理，因为它们已经被分组处理过了 (除非它们是未能分组的 DCD 文件)
#             elif filename.lower().startswith('mke'): # 这是处理未能分组的 MKE 文件
#                 # 原有的按文件类型处理逻辑
#                 process_mke_group(file_path, filename) # 假设 process_mke_file 仍用于单个 MKE 文件
#             else:
#                 # TBD: Handle other files. For now, just log and move.
#                 logging.warning(f"No specific processor defined for file. Moving without processing.")

#             # On success, move the original file to the processed directory
#             processed_path = os.path.join(PROCESSED_DIR, filename)
#             shutil.move(file_path, processed_path)
#             logging.info(f"Moved individual file to:")
#         except Exception as e:
#             logging.error(f"Error processing individual file")
#             try:
#                 # On failure, move the original file to the error directory
#                 error_path = os.path.join(ERROR_DIR, filename)
#                 shutil.move(file_path, error_path)
#                 logging.info(f"Moved failed individual file to")
#             except Exception as move_e:
#                 logging.error(
#                     f"Could not move failed individual file to error folder")



# class NewFileHandler(FileSystemEventHandler):
#     """A handler for file system events."""

#     def on_created(self, event):
#         # We only care about files, not directories
#         if event.is_directory:
#             return

#         logging.info(f"New file detected: {event.src_path}")
#         # A small delay to ensure the file is fully written before processing
#         time.sleep(1)
#         process_file(event.src_path)



# def initial_scan(directory):
#     """Scans and processes any files that exist on startup."""
#     logging.info(f"Performing initial scan of {directory}...")
#     # for filename in os.listdir(directory):
#     #     # The check for marked files is no longer needed as they are moved.
#     #     file_path = os.path.join(directory, filename)
#     #     if os.path.isfile(file_path):
#     #         # process_file(file_path)
#     process_directory_files(directory)

#     logging.info("Initial scan complete.")



# if __name__ == "__main__":

#     # setup_logging()
#     # logging.info("Starting file processor service...")

#     # # Ensure all necessary directories exist
#     # for path in [SOURCE_DIR, OUTPUT_DIR, PROCESSED_DIR, ERROR_DIR]:
#     #     os.makedirs(path, exist_ok=True)

#     # initial_scan(SOURCE_DIR)

#     # observer = Observer()
#     # observer.schedule(NewFileHandler(), SOURCE_DIR, recursive=False)
#     # observer.start()
#     # logging.info(f"Watching directory: {SOURCE_DIR}")

#     # try:
#     #     while observer.is_alive():
#     #         observer.join(1)
#     # except KeyboardInterrupt:
#     #     observer.stop()
#     # observer.join()
#     # logging.info("File processor service stopped.")


    
#     # data_pd = pd.read_csv(path)
#     # print(data_pd)


import fitz
from paddleocr import PaddleOCR
import re

# 假设PaddleOCR已初始化
ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

def recognize_invoice(pdf_path, use_ocr=False):
    """
    识别PDF发票内容的总流程
    :param pdf_path: PDF文件路径
    :param use_ocr: 是否强制使用OCR (如果发票是扫描件，设为True)
    :return: 包含发票信息的字典
    """
    text = ""
    
    # 1. 尝试直接提取文本
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(pdf_path)
        if len(text.strip()) < 100 or use_ocr:
            print("直接文本提取结果不足，尝试OCR...")
            raise Exception("文本太少，强制进入OCR")
        print("成功提取可搜索文本。")
    except:
        # 2. OCR流程 (如果直接提取失败或文本过少)
        try:
            print("正在进行PDF转图像和OCR识别...")
            doc = fitz.open(pdf_path)
            full_ocr_result = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                from PIL import Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                result = ocr.ocr(img, det=True, cls=True)
                page_text = [line[1][0] for line in result[0] if line]
                full_ocr_result.extend(page_text)
                
            text = "\n".join(full_ocr_result)
            print("OCR完成。")
        except Exception as e:
            print(f"OCR处理失败: {e}")
            return {"error": "无法处理文件或执行OCR"}

    # 3. 结构化数据提取
    if not text:
        return {"error": "未能提取任何文本"}

    extracted_data = extract_invoice_data(text)
    
    # 辅助调试：打印提取到的全文
    # print("\n--- Extracted Full Text ---\n", text[:1000])
    
    return extracted_data

# 最终调用示例：
# invoice_data = recognize_invoice('invoice_sample.pdf', use_ocr=False) 
# print(invoice_data)    
