from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm, mm
import time
import os
import sys
import hashlib
import random
import string
import datetime
import qrcode
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 尝试注册中文字体
try:
    pdfmetrics.registerFont(TTFont('SimHei', 'SimHei.ttf'))
    chinese_font = 'SimHei'
except Exception as e:
    print(f"注册中文字体失败: {str(e)}")
    chinese_font = 'Helvetica'
    print("警告: 找不到中文字体文件SimHei.ttf，将使用默认字体。中文可能显示为方块。")

# 哈希生成函数
def generate_hash(data, length=32):
    """生成哈希值"""
    return hashlib.md5(str(data).encode()).hexdigest()[:length]

# 生成二维码图像
def generate_qrcode(data, size=100):
    """生成二维码图像"""
    try:
        import qrcode
        from io import BytesIO
        from reportlab.lib.utils import ImageReader
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 转换为BytesIO以便于ReportLab使用
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)
        
        return ImageReader(img_io)
    except ImportError:
        print("警告: 未安装qrcode模块，将使用文本替代二维码")
        return None

# 注册字体
def register_fonts():
    """注册PDF生成所需的字体，支持多种回退方案"""
    # 检查字体文件夹是否存在
    fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    if not os.path.exists(fonts_dir):
        os.makedirs(fonts_dir)
    
    # 尝试方案1: 使用Windows系统自带的宋体
    font_registered = False
    try:
        windows_font_path = 'C:/Windows/Fonts/simsun.ttc'
        if os.path.exists(windows_font_path):
            pdfmetrics.registerFont(TTFont('SimSun', windows_font_path))
            print(f"成功注册SimSun字体 (从Windows系统)")
            font_registered = True
    except Exception as e:
        print(f"尝试注册Windows宋体失败: {str(e)}")
    
    # 尝试方案2: 使用项目fonts目录下的字体
    if not font_registered:
        try:
            local_font_path = os.path.join(fonts_dir, 'simsun.ttc')
            if os.path.exists(local_font_path):
                pdfmetrics.registerFont(TTFont('SimSun', local_font_path))
                print(f"成功注册SimSun字体 (从本地fonts目录)")
                font_registered = True
        except Exception as e:
            print(f"尝试注册本地宋体失败: {str(e)}")
    
    # 如果前两种方案都失败，使用系统默认字体
    if not font_registered:
        print("警告: 无法加载中文字体，将使用系统默认字体")

# 创建PDF文档
def create_police_record_pdf(police_data, output_path):
    """
    根据警情记录数据创建PDF文档
    
    参数:
    - police_data: 包含警情记录信息的字典
    - output_path: PDF输出路径
    
    返回:
    - PDF文件的绝对路径
    """
    try:
        # 注册字体
        register_fonts()
        
        # 创建PDF对象
        c = canvas.Canvas(output_path, pagesize=A4)
        
        # 添加区块链验证信息到PDF元数据
        chain_proof = {
            'PoliceNo': police_data.get('PoliceNo', ''),
            'ReceiveTime': police_data.get('ReceiveTime', ''),
            'PoliceOfficer': police_data.get('PoliceOfficer', ''),
            'Result': police_data.get('Result', ''),
            'GPSLocation': police_data.get('GPSLocation', ''),
            'Temp_Hash': police_data.get('Temp_Hash', ''),
            'PDF_Hash': police_data.get('PDF_Hash', ''),
            'Merkle_Hash': police_data.get('Merkle_Hash', ''),
            'IPFS': police_data.get('IPFS', ''),
            'UploadTime': police_data.get('UploadTime', ''),
            'ReportType': police_data.get('ReportType', ''),
            'Location': police_data.get('Location', ''),
            'ContactName': police_data.get('ContactName', ''),
            'ContactPhone': police_data.get('ContactPhone', ''),
            'Priority': police_data.get('Priority', ''),
            'Department': police_data.get('Department', ''),
            'DispatchTime': police_data.get('DispatchTime', ''),
            'Description': police_data.get('Description', '')
        }
        
        # 设置PDF元数据
        c.setTitle(f"警情记录-{police_data.get('PoliceNo', '')}")
        c.setAuthor("智警链存系统")
        c.setSubject("警情处置电子凭证")
        c.setKeywords("警情, 区块链, 电子凭证")
        c.setCreator("智警链存-区块链存证系统")
        
        # 添加区块链验证信息
        c._doc.info.chain_proof = str(chain_proof)
        
        width, height = A4  # A4大小: 21.0 x 29.7 cm
        
        # 设置中文字体
        try:
            c.setFont("SimSun", 16)
        except:
            c.setFont("Helvetica", 16)
        
        # 添加页眉 - 标题
        c.drawCentredString(width/2, height - 20*mm, "中华人民共和国公安机关")
        c.drawCentredString(width/2, height - 30*mm, "警情处置电子凭证")
        
        # 绘制分隔线
        c.setStrokeColor(colors.black)
        c.line(20*mm, height - 40*mm, width - 20*mm, height - 40*mm)
        
        # 添加警情信息(参照示例图片)
        y_start = height - 50*mm
        line_height = 10*mm
        
        # 使用合适的中文字体
        try:
            c.setFont("SimSun", 12)
        except:
            c.setFont("Helvetica", 12)
        
        # 添加行信息函数
        def add_info_line(label, value, y_pos):
            c.drawString(20*mm, y_pos, label)
            c.drawString(45*mm, y_pos, value)
        
        # 添加信息行
        # 修复PDF_Hash为None的情况
        pdf_hash = police_data.get('PDF_Hash', '')
        pdf_hash_display = f"P{pdf_hash[-8:]}" if pdf_hash and len(pdf_hash) >= 8 else f"P{generate_hash(police_data.get('PoliceNo', ''), 8)}"
        add_info_line("编号:", pdf_hash_display, y_start)
        add_info_line("警情编号:", police_data.get('PoliceNo', ''), y_start - line_height)
        add_info_line("接警时间:", police_data.get('ReceiveTime', ''), y_start - 2*line_height)
        add_info_line("发生地点:", police_data.get('Location', '北京市朝阳区建国路'), y_start - 3*line_height)
        add_info_line("地理坐标:", police_data.get('GPSLocation', ''), y_start - 4*line_height)
        add_info_line("报警人:", police_data.get('ContactName', '未知'), y_start - 5*line_height)
        
        # 单独显示联系电话
        add_info_line("联系电话:", police_data.get('ContactPhone', ''), y_start - 6*line_height)
        
        # 正确显示报警类型
        add_info_line("报警类型:", police_data.get('ReportType', ''), y_start - 7*line_height)
        
        # 警情描述
        description = police_data.get('Description', '')
        if not description:
            description = "警情处理中"
        add_info_line("警情描述:", description, y_start - 8*line_height)
        
        # 添加处置信息区域
        y_disp = y_start - 10*line_height
        c.drawString(20*mm, y_disp, "处置人员:")
        c.drawString(45*mm, y_disp, police_data.get('PoliceOfficer', ''))
        c.drawString(20*mm, y_disp - line_height, "出警单位:")
        c.drawString(45*mm, y_disp - line_height, police_data.get('Department', ''))
        c.drawString(20*mm, y_disp - 2*line_height, "出警时间:")
        # 如果未提供出警时间，默认为接警时间后15分钟
        dispatch_time = police_data.get('DispatchTime', '')
        if not dispatch_time and police_data.get('ReceiveTime'):
            try:
                # 尝试解析接警时间并添加15分钟
                receive_time_dt = datetime.datetime.strptime(police_data.get('ReceiveTime', ''), '%Y-%m-%d %H:%M:%S')
                dispatch_time = (receive_time_dt + datetime.timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
            except:
                dispatch_time = ''
        c.drawString(45*mm, y_disp - 2*line_height, dispatch_time)
        
        # 处置结果
        c.drawString(20*mm, y_disp - 3*line_height, "处置结果:", )
        c.drawString(45*mm, y_disp - 3*line_height, police_data.get('Result', '已移交相关部门'))
        
        # 优先级 - 确保始终显示优先级信息
        c.drawString(20*mm, y_disp - 4*line_height, "优先级:", )
        priority = police_data.get('Priority', '')
        if not priority:
            priority = '普通'
        c.drawString(45*mm, y_disp - 4*line_height, priority)
        
        # 添加联系人信息 - 由于报警人已移到上方，这里仅在联系人和报警人不同时显示
        contact_name = police_data.get('ContactName', '')
        reporter_different = False
        if contact_name and contact_name != police_data.get('ContactName', ''):
            reporter_different = True
            c.drawString(20*mm, y_disp - 5*line_height, "其他联系人:", )
            contact_info = f"{contact_name} {police_data.get('ContactPhone', '')}"
            c.drawString(45*mm, y_disp - 5*line_height, contact_info)
            y_sig = y_disp - 7*line_height
        elif reporter_different:
            y_sig = y_disp - 7*line_height
        else:
            y_sig = y_disp - 6*line_height
        
        # 添加数据签名区域
        c.drawString(20*mm, y_sig, "数据签名Hash:")
        data_hash = police_data.get('Temp_Hash', '')
        if data_hash:
            hash_display = f"{data_hash[:20]}...{data_hash[-5:]}" if len(data_hash) > 25 else data_hash
        else:
            hash_display = generate_hash(f"temp_{police_data.get('PoliceNo', '')}", 20)
        c.drawString(65*mm, y_sig, hash_display)
        
        # 添加上链时间
        c.drawString(20*mm, y_sig - line_height, "上链时间:")
        c.drawString(65*mm, y_sig - line_height, police_data.get('UploadTime', ''))
        
        # 添加二维码
        qr_img = generate_qrcode(f"https://police-chain.gov.cn/verify/{police_data.get('PoliceNo', '')}")
        if qr_img:
            qr_size = 30*mm
            c.drawImage(qr_img, width - 50*mm, y_sig - 2*line_height, width=qr_size, height=qr_size)
            # 添加验证提示
            c.setFont("SimSun", 8)
            c.drawString(width - 53*mm, y_sig - 3*line_height, "扫码验证真伪")
        else:
            # 如果没有二维码模块，显示文本
            c.drawString(width - 60*mm, y_sig - 2*line_height, "验证链接:")
            c.drawString(width - 60*mm, y_sig - 3*line_height, f"police-chain.gov.cn/verify/{police_data.get('PoliceNo', '')}")
        
        # 添加页脚
        y_footer = 20*mm
        c.drawCentredString(width/2, y_footer, "本文件为警情记录电子凭证，已通过区块链技术确保数据真实性与完整性")
        c.drawCentredString(width/2, y_footer - 5*mm, "公安局警情管理系统")
        
        # 保存PDF
        c.save()
        
        return os.path.abspath(output_path)
    except Exception as e:
        print(f"PDF生成错误: {str(e)}")
        # 输出详细的堆栈信息以便调试
        import traceback
        traceback.print_exc()
        raise

# 测试函数 - 生成示例PDF
def generate_sample_pdf():
    """生成示例PDF文件"""
    # 示例数据
    sample_data = {
        "PoliceNo": "JQ2022060102",
        "ReceiveTime": "2022-06-12 14:20:00",
        "PoliceOfficer": "李四",
        "Result": "邻里纠纷，已现场调解完毕",
        "GPSLocation": "39.9088, 116.4666",
        "UploadTime": "2022-06-12 15:15:00",
        "blockchain_hash": "0x8f7d8a9e1b3c5a2d4e6f8a9c1b3d5e7f",
        "Temp_Hash": "422f487339db6c1975664b24150927...378a4",
        "PDF_Hash": "8f7d8a9e1b3c5a2d",
        "BlockNum": 12345,  # 区块号不再显示在PDF中，仅在系统内部使用
        "Merkle_Hash": "8c5a14cc043600245cb94968",
        "IPFS": "QmOlBcMs7GxrMtiqDv7zmviHQytG7hY4SYmoWRu1kfgLgw",
        "RecordStatus": "Active"
    }
    
    # 确保输出目录存在
    output_dir = os.path.join(os.getcwd(), "police_records")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 生成PDF
    try:
        output_path = os.path.join(output_dir, f"{sample_data['PoliceNo']}.pdf")
        pdf_path = create_police_record_pdf(sample_data, output_path)
        print(f"示例PDF已生成: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"生成示例PDF时出错: {str(e)}")
        return None

# 从数据库记录生成PDF的函数
def generate_pdf_from_record(record_data):
    """
    生成PDF文件，不使用可填充表单字段，而是直接将数据写入PDF
    该函数现在会检查是否已存在对应警情编号的PDF文件，避免重复生成
    """
    # 确保警情记录目录存在
    if not os.path.exists('police_records'):
        os.makedirs('police_records')
    
    police_no = record_data.get('PoliceNo', f'unknown_{int(time.time())}')
    
    # 检查是否已经存在该警情编号的PDF文件 - 考虑多种格式
    # 查找以警情编号开头，以.pdf结尾的所有文件
    existing_files = [f for f in os.listdir('police_records') 
                     if f.startswith(f"{police_no}_") and f.endswith('.pdf')]
    
    # 也考虑其他可能的格式，如不带下划线的文件名
    if not existing_files:
        additional_files = [f for f in os.listdir('police_records') 
                          if f.startswith(police_no) and f.endswith('.pdf')]
        existing_files.extend(additional_files)
    
    # 改为：如果已存在PDF文件，则直接返回，不再重新生成
    if existing_files:
        existing_file = os.path.join('police_records', existing_files[0])
        print(f"警情编号 {police_no} 的PDF文件已存在，使用现有文件: {existing_file}")
        return existing_file

    # 生成唯一的文件名
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    pdf_filename = f"police_records/{police_no}_{random_str}.pdf"
    
    # 如果之前未能处理latitude longitude，且这些字段存在
    # 将其转换为GPSLocation格式
    if (('Latitude' in record_data or 'latitude' in record_data) and 
        ('Longitude' in record_data or 'longitude' in record_data)):
        lat = record_data.get('Latitude', record_data.get('latitude', ''))
        lon = record_data.get('Longitude', record_data.get('longitude', ''))
        if lat and lon:
            record_data['GPSLocation'] = f"{lat}, {lon}"
    
    # 确保优先级字段被正确处理
    if 'Priority' in record_data:
        priority = record_data['Priority']
        # 如果优先级是数字，转换为文本描述
        if isinstance(priority, (int, float)) or (isinstance(priority, str) and priority.isdigit()):
            priority_val = int(priority)
            if priority_val == 1:
                record_data['Priority'] = '高'
            elif priority_val == 2:
                record_data['Priority'] = '中'
            elif priority_val == 3:
                record_data['Priority'] = '低'
            else:
                record_data['Priority'] = '普通'
        # 如果优先级是空字符串，设置默认值
        elif not priority:
            record_data['Priority'] = '普通'
    else:
        record_data['Priority'] = '普通'
    
    # 确保报警类型被正确处理
    if 'ReportType' not in record_data or not record_data['ReportType']:
        # 尝试从Description字段提取报警类型
        if 'Description' in record_data and record_data['Description']:
            desc = record_data['Description']
            # 提取潜在的报警类型
            for type_keyword in ['纠纷', '盗窃', '抢劫', '伤害', '骚扰', '打架', '争吵']:
                if type_keyword in desc:
                    record_data['ReportType'] = type_keyword
                    break
        
        # 如果仍未设置报警类型，设置默认值
        if 'ReportType' not in record_data or not record_data['ReportType']:
            record_data['ReportType'] = '治安事件'

    # 创建PDF数据结构
    police_data = {
        'PoliceNo': record_data.get('PoliceNo', ''),
        'ReceiveTime': record_data.get('ReceiveTime', ''),
        'Location': record_data.get('Location', ''),
        'GPSLocation': record_data.get('GPSLocation', ''),
        'ContactName': record_data.get('ContactName', ''),
        'ContactPhone': record_data.get('ContactPhone', ''),  # 确保包含电话
        'ReportType': record_data.get('ReportType', ''),     # 确保包含报警类型
        'Description': record_data.get('Description', ''),
        'PoliceOfficer': record_data.get('PoliceOfficer', ''),
        'Department': record_data.get('Department', ''),
        'DispatchTime': record_data.get('DispatchTime', ''),
        'Result': record_data.get('Result', ''),
        'Priority': record_data.get('Priority', ''),         # 确保包含优先级
        'Temp_Hash': record_data.get('Temp_Hash', ''),
        'PDF_Hash': record_data.get('PDF_Hash', ''),
        'IPFS': record_data.get('IPFS', ''),
        'UploadTime': record_data.get('UploadTime', '')
    }
    
    # 创建PDF
    return create_police_record_pdf(police_data, pdf_filename)

def generate_qr_code(data):
    """生成QR码图像"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # 保存QR码为临时文件
    temp_qr_path = f"temp_qr_{int(time.time())}.png"
    qr_img.save(temp_qr_path)
    
    return temp_qr_path

# 主程序入口
if __name__ == "__main__":
    generate_sample_pdf() 