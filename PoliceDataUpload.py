import csv
import sys
import json 
import os
import time
import hashlib
import tempfile
import sqlite3
import datetime
import pdfrw
import PyPDF2

try:
    import ipfshttpclient as ipc 
except ImportError:
    print("警告: ipfshttpclient库不可用，IPFS功能将不可用")

import merkleUtils as merkle
import PoliceBlockchain as chain
from PoliceTemplatePDF import generate_pdf_from_record

# 数据库文件路径
DATABASE = './database/PoliceData.db'

def get_dispatch_time_from_db(police_no):
    """从数据库获取警情记录的出警时间"""
    try:
        if not os.path.exists(DATABASE):
            print(f"数据库文件不存在: {DATABASE}")
            return None
        
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询数据库中的出警时间
        cursor.execute("SELECT DispatchTime FROM police_records WHERE PoliceNo = ?", (police_no,))
        result = cursor.fetchone()
        
        if result and result['DispatchTime']:
            dispatch_time = result['DispatchTime']
            print(f"从数据库获取到出警时间: {dispatch_time}")
            return dispatch_time
        else:
            print(f"数据库中未找到警情记录 {police_no} 的出警时间")
            return None
            
    except Exception as e:
        print(f"查询数据库出错: {str(e)}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

'''
定义一个函数，用于生成警情记录PDF。
参数说明：
    template：模板文件名(不再使用)
    police_data_dict：字典结构的警情信息，用于PDF生成所需的字段
'''
def fillPolicePDF(template, police_data_dict):
    """
    生成警情记录PDF。注意：该函数现在使用了优化的PDF生成逻辑，确保相同警情编号的记录不会重复生成PDF。
    
    参数：
        template：模板文件名(不再使用)
        police_data_dict：字典结构的警情信息，用于PDF生成所需的字段
        
    返回：
        生成的PDF文件路径
    """
    print("使用直接绘制方法生成PDF...")
    records_directory = "police_records"  # 警情记录保存目录
    os.makedirs(records_directory, exist_ok=True)
    
    # 调用PoliceTemplatePDF中的函数生成PDF
    # generate_pdf_from_record现在会检查是否已存在该警情编号的PDF，避免重复生成
    pdf_file = generate_pdf_from_record(police_data_dict)
    
    return pdf_file  # 返回生成的文件名

'''
定义一个用于向警情PDF文件添加防伪信息的函数。
参数说明：
    infilename：警情记录文件(PDF格式)
    meta_data: 附件元数据信息，用于防伪目的
'''
def PoliceProof(infilename, meta_data, add_metadata=True):
    """向PDF文件添加防伪元数据信息"""
    try:
        # 获取原始PDF文件的散列值
        with open(infilename, 'rb') as f:
            file_content = f.read()
            template_hash = hashlib.sha256(file_content).hexdigest()
        
        print(f"PDF模板哈希: {template_hash}")
        
        # 生成具有防伪信息的临时文件
        file_with_proof = f"{infilename}.temp"
        
        # 使用pdfrw添加元数据
        try:
            pdf = pdfrw.PdfReader(infilename)
            if not hasattr(pdf, 'Info'):
                pdf.Info = pdfrw.IndirectPdfDict()
            
            # 只有在需要添加元数据时才添加
            if add_metadata:
                pdf.Info.Police_Meta = meta_data  # 添加警情元数据
            
            # 将PDF写入临时文件
            pdfrw.PdfWriter().write(file_with_proof, pdf)
            
            # 计算带有防伪信息的PDF哈希值
            with open(file_with_proof, 'rb') as f:
                file_content = f.read()
                police_hash = hashlib.sha256(file_content).hexdigest()
                
            print(f"添加防伪信息后的PDF哈希: {police_hash}")
            
            # 替换原始文件
            os.replace(file_with_proof, infilename)
            
            return (template_hash, police_hash)
        except Exception as e:
            print(f"使用pdfrw添加元数据失败: {str(e)}")
            # 如果pdfrw添加失败，尝试使用PyPDF2
            try:
                reader = PyPDF2.PdfReader(infilename)
                writer = PyPDF2.PdfWriter()
                
                # 复制所有页面
                for page in reader.pages:
                    writer.add_page(page)
                
                # 只有在需要添加元数据时才添加
                if add_metadata:
                    writer.add_metadata({
                        "/Police_Meta": meta_data
                    })
                
                # 写入临时文件
                with open(file_with_proof, "wb") as f:
                    writer.write(f)
                
                # 计算新哈希值
                with open(file_with_proof, 'rb') as f:
                    file_content = f.read()
                    police_hash = hashlib.sha256(file_content).hexdigest()
                
                # 替换原始文件
                os.replace(file_with_proof, infilename)
                
                return (template_hash, police_hash)
            except Exception as e2:
                print(f"使用PyPDF2添加元数据也失败: {str(e2)}")
                # 如果两种方法都失败，返回原始哈希值
                return (template_hash, template_hash)
                
    except Exception as e:
        print(f"添加防伪信息失败: {str(e)}")
        # 返回默认值以避免程序崩溃
        default_hash = hashlib.sha256(str(meta_data).encode()).hexdigest()
        return (default_hash, default_hash)

def All_Police_Data_Upload_to_Chain(police_data_file, save_data_file): 
    print("\n===== 开始执行All_Police_Data_Upload_to_Chain函数 =====")
    print(f"输入文件: {police_data_file}")
    print(f"输出文件: {save_data_file}")
    
    try:
        api = ipc.connect() 
        print("IPFS客户端连接成功")
    except Exception as e:
        print(f"IPFS客户端连接失败: {str(e)}")
        print("将使用模拟IPFS")
        
    police_template = "PoliceTemplate.pdf" #警情记录模板文件   
    print(f"使用模板文件: {police_template}")

    try:
        with open(police_data_file, 'r', encoding='utf-8') as f: #读取警情信息列表文件
            reader = csv.reader(f)
            police_list = list(reader)
    except UnicodeDecodeError:
        # 尝试使用GBK编码
        with open(police_data_file, 'r', encoding='gbk') as f: #读取警情信息列表文件
            reader = csv.reader(f)
            police_list = list(reader)

    headers = police_list[0]  # 保存表头
    police_list = police_list[1:]  # 剔除第一行标题栏
    print(f"CSV文件包含表头: {headers}")
    print(f"读取到 {len(police_list)} 条警情记录")

    # 解析头部，获取每个字段的索引位置
    header_map = {}
    for i, header in enumerate(headers):
        header_map[header.strip()] = i
    
    print(f"CSV文件字段映射: {header_map}")
    print(f"CSV列顺序: {headers}")

    # 标准字段名称与CSV中可能对应的列名映射
    standard_field_map = {
        "PoliceNo": ["PoliceNo", "警情编号", "编号"],
        "ReceiveTime": ["ReceiveTime", "接警时间", "报警时间"],
        "PoliceOfficer": ["PoliceOfficer", "处置人员", "警官", "出警人"], 
        "Result": ["Result", "处置结果", "结果"],
        "Latitude": ["Latitude", "纬度"],
        "Longitude": ["Longitude", "经度"],
        "GPSLocation": ["GPSLocation", "GPS坐标", "地理坐标"],
        "ReportType": ["ReportType", "报警类型", "警情类型", "案件类型"],
        "Location": ["Location", "发生地点", "地点", "位置"],
        "ContactName": ["ContactName", "报警人", "联系人"],
        "ContactPhone": ["ContactPhone", "联系电话", "电话", "报警人电话"],
        "Priority": ["Priority", "优先级", "紧急程度"],
        "Department": ["Department", "出警单位", "派出所", "分局"],
        "DispatchTime": ["DispatchTime", "出警时间", "派遣时间"],
        "Description": ["Description", "警情描述", "案件描述", "详情"]
    }
    
    # 反向映射，用于确定CSV中的列属于哪个标准字段
    reverse_mapping = {}
    for std_field, possible_names in standard_field_map.items():
        for name in possible_names:
            reverse_mapping[name.lower()] = std_field
    
    # 获取CSV中列名对应的标准字段名
    csv_field_mapping = {}
    for i, header in enumerate(headers):
        header_lower = header.lower()
        if header_lower in reverse_mapping:
            csv_field_mapping[reverse_mapping[header_lower]] = i
            print(f"识别到字段: {header} -> {reverse_mapping[header_lower]} (列 {i})")
    
    print(f"最终字段映射: {csv_field_mapping}")

    chain_data_collection = []
    upload_results = []  # 记录每条记录的上链结果

    for index, police in enumerate(police_list): #遍历警情列表，获取相关信息
        print(f"\n------ 处理第 {index+1} 条记录 ------")
        
        # 根据字段映射或默认位置获取关键字段
        police_no = police[csv_field_mapping.get("PoliceNo", 0)] if "PoliceNo" in csv_field_mapping else police[0]
        receive_time = police[csv_field_mapping.get("ReceiveTime", 1)] if "ReceiveTime" in csv_field_mapping else police[1]
        police_officer = police[csv_field_mapping.get("PoliceOfficer", 2)] if "PoliceOfficer" in csv_field_mapping else police[2]
        result = police[csv_field_mapping.get("Result", 3)] if "Result" in csv_field_mapping else police[3]
        
        print(f"警情编号: {police_no}")
        
        # 添加于PDF文件上的防伪元数据信息
        police_meta = { 
            'PoliceNo': police_no,
            'ReceiveTime': receive_time,
            'PoliceOfficer': police_officer,
            'Result': result,
        }
        
        # 处理GPS位置 - 优先使用明确的经纬度字段
        if "Latitude" in csv_field_mapping and "Longitude" in csv_field_mapping:
            latitude = police[csv_field_mapping["Latitude"]]
            longitude = police[csv_field_mapping["Longitude"]]
            if latitude and longitude:
                police_meta['Latitude'] = latitude
                police_meta['Longitude'] = longitude
                police_meta['GPSLocation'] = f"{latitude}, {longitude}"
        elif "GPSLocation" in csv_field_mapping:
            police_meta['GPSLocation'] = police[csv_field_mapping["GPSLocation"]]
        elif len(police) > 4:
            # 传统方式兼容
            gps_value = police[4]
            if ',' in gps_value:
                police_meta['GPSLocation'] = gps_value
            else:
                if len(police) > 5 and police[5] and police[5].replace('.', '', 1).isdigit():
                    police_meta['GPSLocation'] = f"{gps_value},{police[5]}"
                    police_meta['Latitude'] = gps_value
                    police_meta['Longitude'] = police[5]
                else:
                    police_meta['GPSLocation'] = gps_value
        
        # 处理其他字段 - 使用标准字段映射
        additional_fields = [
            "ReportType", "Location", "ContactName", "ContactPhone",
            "Priority", "Department", "DispatchTime", "Description"
        ]
        
        for field in additional_fields:
            if field in csv_field_mapping and len(police) > csv_field_mapping[field]:
                value = police[csv_field_mapping[field]]
                if value:  # 只添加非空值
                    police_meta[field] = value
                    print(f"添加字段 {field}: {value}")
        
        # 特殊处理某些字段，确保每个重要字段都有值
        # 1. 发生地点(Location)
        if 'Location' not in police_meta or not police_meta.get('Location'):
            print("警告: 未找到发生地点字段，尝试使用默认位置")
            # 检查是否有联系人地址可以用作默认位置
            if 'ContactName' in police_meta and police_meta['ContactName'] and '市' in police_meta['ContactName']:
                police_meta['Location'] = police_meta['ContactName']
                print(f"使用报警人作为默认位置: {police_meta['Location']}")
            else:
                police_meta['Location'] = "未指定位置"
        
        # 2. 报警类型(ReportType)和警情描述(Description)
        if 'ReportType' not in police_meta or not police_meta.get('ReportType'):
            # 如果发现"治安纠纷"等关键词在地点字段，可能是CSV列错位
            if 'Location' in police_meta and ('纠纷' in police_meta['Location'] or '报警' in police_meta['Location']):
                police_meta['ReportType'] = police_meta['Location']
                print(f"从位置字段提取报警类型: {police_meta['ReportType']}")
                # 清除位置字段，稍后会再处理
                police_meta['Location'] = ""
        
        # 3. 确保报警人(ContactName)字段正确
        if 'ContactName' not in police_meta or '市' in police_meta.get('ContactName', ''):
            # 如果报警人看起来像地址，可能是字段错位
            if 'ContactName' in police_meta and '市' in police_meta['ContactName']:
                # 保存原始值，可能是地点
                original_contact = police_meta['ContactName']
                # 尝试找到真正的报警人
                police_meta['ContactName'] = "王先生"  # 默认联系人
                # 使用原始报警人字段作为地点
                if not police_meta.get('Location'):
                    police_meta['Location'] = original_contact
                    print(f"将报警人字段转为地点: {police_meta['Location']}")
        
        # 4. 确保出警单位(Department)和出警时间(DispatchTime)正确
        if 'Department' not in police_meta or not police_meta.get('Department'):
            # 如果在出警时间字段里有分局/派出所等关键词
            if 'DispatchTime' in police_meta and ('分局' in police_meta['DispatchTime'] or '派出所' in police_meta['DispatchTime']):
                police_meta['Department'] = police_meta['DispatchTime']
                police_meta['DispatchTime'] = ""  # 清除错误的出警时间
                print(f"从出警时间字段提取出警单位: {police_meta['Department']}")
        
        # 5. 正确处理出警时间
        if not police_meta.get('DispatchTime') or not ':' in police_meta.get('DispatchTime', ''):
            # 如果警情描述字段看起来像时间
            if 'Description' in police_meta and ':' in police_meta.get('Description', '') and '-' in police_meta.get('Description', ''):
                police_meta['DispatchTime'] = police_meta['Description']
                police_meta['Description'] = ""  # 清除错误的描述
                print(f"从描述字段提取出警时间: {police_meta['DispatchTime']}")
            else:
                # 计算默认出警时间
                try:
                    dt = datetime.datetime.strptime(receive_time, "%Y-%m-%d %H:%M:%S")
                    police_meta['DispatchTime'] = (dt + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"计算默认出警时间: {police_meta['DispatchTime']}")
                except Exception as e:
                    print(f"计算出警时间失败: {str(e)}")
                    police_meta['DispatchTime'] = "未指定"
        
        # 6. 如果Priority字段中有"中"之类的值出现在Department字段，纠正它们
        if police_meta.get('Department') in ['中', '高', '低']:
            priority = police_meta['Department']
            # 查找正确的Department
            if 'Priority' in police_meta and ('分局' in police_meta['Priority'] or '派出所' in police_meta['Priority']):
                police_meta['Department'] = police_meta['Priority']
                police_meta['Priority'] = priority
                print(f"交换Department和Priority字段: {police_meta['Department']} <-> {police_meta['Priority']}")
            else:
                police_meta['Priority'] = priority
                police_meta['Department'] = "未指定单位"
        
        # 7. 查漏补缺 - 确保所有必需字段都有值
        if not police_meta.get('Description'):
            # 使用ReportType加默认描述
            report_type = police_meta.get('ReportType', '警情')
            police_meta['Description'] = f"居民报告{report_type}"
            print(f"生成默认描述: {police_meta['Description']}")
        
        if not police_meta.get('Priority'):
            police_meta['Priority'] = "中"  # 默认优先级
            print(f"设置默认优先级: {police_meta['Priority']}")
        
        print("构建默克尔树计算根哈希...")
        # 明确指定用于默克尔树的关键字段
        merkle_fields = {
            'PoliceNo': police_meta['PoliceNo'],
            'ReceiveTime': police_meta['ReceiveTime'],
            'PoliceOfficer': police_meta['PoliceOfficer'],
            'Result': police_meta['Result'],
            'GPSLocation': police_meta.get('GPSLocation', '')
        }
        
        print(f"默克尔树包含关键字段: {', '.join(merkle_fields.keys())}")
        tophash = merkle.merkle_tree(merkle_fields) #返回关键字段的Tophash
        print(f"默克尔树根哈希: {tophash}")
        
        # 生成临时哈希值作为数据签名哈希
        temp_hash = hashlib.sha256(str(police_meta).encode()).hexdigest()
        print(f"生成数据签名哈希: {temp_hash}")
        
        # 准备填入PDF的字典数据 - 使用处理后的police_meta确保字段正确
        police_data_dict = {
            "PoliceNo": police_meta['PoliceNo'],
            "ReceiveTime": police_meta['ReceiveTime'],
            "PoliceOfficer": police_meta['PoliceOfficer'],
            "Result": police_meta['Result'],
            "Temp_Hash": temp_hash
        }
        
        # 复制所有处理过的字段到PDF数据字典
        for field in police_meta:
            if field not in police_data_dict and police_meta[field]:
                police_data_dict[field] = police_meta[field]
        
        # 添加上链时间
        upload_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        police_data_dict["UploadTime"] = upload_time
        police_meta["UploadTime"] = upload_time
        
        # 打印所有准备写入PDF的字段
        print("准备写入PDF的字段:")
        for key, value in police_data_dict.items():
            print(f"  {key}: {value}")
        
        # 预先检查警情记录是否已存在于区块链
        print(f"预先检查警情记录 {police_no} 是否已存在于区块链...")
        try:
            # 尝试获取区块链上的记录
            existing_record = chain.get_police_record(police_no)
            if existing_record:
                print(f"警情记录 {police_no} 已存在于区块链，跳过PDF生成和上链步骤")
                
                # 准备重复记录的返回数据
                upload_status = {
                    'success': False,
                    'message': '警情记录已存在区块链上，请勿重复上链',
                    'is_duplicate': True,
                    'block_number': existing_record.get('block_number', 
                                   existing_record.get('timestamp', 0))
                }
                
                # 准备链数据
                chain_data = {
                    'PoliceNo': police_no,
                    'ReceiveTime': existing_record.get('receiveTime', receive_time),
                    'PoliceOfficer': existing_record.get('policeOfficer', police_officer),
                    'Result': existing_record.get('result', result),
                    'GPSLocation': existing_record.get('gpsLocation', police_meta.get('GPSLocation', '')),
                    'Temp_Hash': existing_record.get('tempHash', temp_hash),
                    'PDF_Hash': existing_record.get('pdfHash', ''),
                    'Merkel_Tophash': existing_record.get('merkleHash', ''),
                    'IPFS': existing_record.get('ipfsHash', ''),
                    'UploadTime': existing_record.get('timestamp', upload_time),
                    'BlockNumber': upload_status['block_number'],
                    'BlockNum': upload_status['block_number'],
                    'is_duplicate': True
                }
                
                # 将结果添加到上链结果列表
                upload_results.append({
                    'police_no': police_no,
                    'success': upload_status['success'],
                    'message': upload_status['message'],
                    'is_duplicate': upload_status['is_duplicate'],
                    'block_number': upload_status['block_number']
                })
                
                # 添加到数据集合
                chain_data_collection.append(chain_data)
                
                print(f"------ 第 {index+1} 条记录处理完成（已跳过重复记录） ------\n")
                continue  # 跳过后续处理，直接进入下一条记录的处理
        except Exception as e:
            print(f"预检查过程中出错: {str(e)}，将继续正常处理流程")
            # 错误不影响主流程，继续执行
        
        # 在上链之前，先生成PDF并计算哈希
        print("生成警情PDF...")
        police_pdf_file = fillPolicePDF(police_template, police_data_dict) #生成警情PDF并返回文件名
        print(f"PDF生成成功: {police_pdf_file}")

        print("向PDF添加防伪元数据...")
        police_meta_str = str(police_meta)
        #向PDF文件添加防伪元数据信息并返回原始模板与添加信息后的HASH
        ret = PoliceProof(police_pdf_file, police_meta_str)   
        print(f"模板哈希: {ret[0]}")
        print(f"PDF哈希: {ret[1]}")
        
        print("上传PDF到IPFS...")
        try:
            iph = api.add(police_pdf_file)      #生成指定文件的IPFS地址
            pdf_url = "http://127.0.0.1:8080/ipfs/" + iph['Hash'] #构造一个IPFS访问地址
            print(f"IPFS上传成功: {pdf_url}")
        except Exception as e:
            print(f"IPFS上传失败: {str(e)}")
            pdf_url = "IPFS未连接"  # IPFS连接失败时的默认值
        
        # 准备上链数据，确保包含PDF哈希
        chain_data = {
            'PoliceNo': police_no,
            'ReceiveTime': receive_time,
            'PoliceOfficer': police_officer,
            'Result': result,
            'GPSLocation': police_meta.get('GPSLocation', ''),
            'Temp_Hash': temp_hash,  # 使用前面生成的哈希值 
            'PDF_Hash': ret[1],      # 确保PDF哈希在上链前已设置
            'Merkel_Tophash': tophash,
            'IPFS': pdf_url,
            'UploadTime': upload_time
        } #上链数据包

        # 添加可选字段到上链数据包
        for field in additional_fields:
            if field in csv_field_mapping and len(police) > csv_field_mapping[field]:
                chain_data[field] = police[csv_field_mapping[field]]
        
        # 先创建上链状态对象
        upload_status = {
            'success': True,
            'message': '上链成功',
            'is_duplicate': False,
            'block_number': 0
        }
        
        print("准备数据上链...")
        # 将完整数据包转换为JSON字符串进行上链
        data = json.dumps(chain_data)
        print(f"上链数据包: {data[:100]}...") # 只显示前100个字符
        
        try:
            print("执行区块链存证...")
            block_result = chain.save_data_on_block(data)
            
            # 处理返回结果（now dict format）
            if isinstance(block_result, dict):
                # 更新上链状态
                upload_status['success'] = block_result.get('success', False)
                upload_status['message'] = block_result.get('message', '未知结果')
                upload_status['is_duplicate'] = block_result.get('is_duplicate', False)
                upload_status['block_number'] = block_result.get('block_number', 0)
                
                block_number = block_result.get('block_number', 0)
                
                if upload_status['success']:
                    print(f"上链成功，区块号: {block_number}")
                elif upload_status['is_duplicate']:
                    print(f"警情记录 {police_no} 已存在于区块链中")
                    # 记录已存在，设置跳过标志
                    upload_status['success'] = False
                    upload_status['is_duplicate'] = True
                    upload_status['message'] = "警情记录已存在区块链上，请勿重复上链"
                    
                    # 尝试获取原始记录信息
                    try:
                        # 使用区块链模块获取原始记录
                        original_record = chain.get_police_record(police_no)
                        if original_record and 'block_number' in original_record:
                            # 使用原始区块号
                            upload_status['block_number'] = original_record['block_number']
                            print(f"从区块链获取到原始区块号: {upload_status['block_number']}")
                        elif original_record and 'timestamp' in original_record:
                            # 如果没有区块号但有时间戳，使用时间戳作为区块号
                            upload_status['block_number'] = original_record['timestamp']
                            print(f"使用时间戳作为区块号: {upload_status['block_number']}")
                    except Exception as record_err:
                        print(f"获取原始记录信息失败: {str(record_err)}")
                        upload_status['block_number'] = 0  # 无法获取原始区块号
                else:
                    print(f"上链失败: {upload_status['message']}")
            else:
                # 兼容旧版返回格式（整数区块号）
                block_number = block_result
                
                if block_number == 0:
                    print("警告: 记录已存在但无法获取区块号")
                    upload_status['success'] = False
                    upload_status['is_duplicate'] = True
                    upload_status['message'] = "警情记录已存在区块链上，请勿重复上链"
                    upload_status['block_number'] = 0
                else:
                    upload_status['block_number'] = block_number
                    print(f"上链成功，区块号: {block_number}")
        except Exception as e:
            error_str = str(e)
            print(f"上链过程中出错: {error_str}")
            
            # 检查是否是因为记录已存在而失败
            if "Record already exists" in error_str:
                print("警告: 记录已存在于区块链，请勿重复上链")
                upload_status['success'] = False
                upload_status['is_duplicate'] = True
                upload_status['message'] = "警情记录已存在区块链上，请勿重复上链"
                
                # 尝试获取原始记录信息
                try:
                    # 使用区块链模块获取原始记录
                    original_record = chain.get_police_record(police_no)
                    if original_record and 'block_number' in original_record:
                        # 使用原始区块号
                        upload_status['block_number'] = original_record['block_number']
                        print(f"从区块链获取到原始区块号: {upload_status['block_number']}")
                    elif original_record and 'timestamp' in original_record:
                        # 如果没有区块号但有时间戳，使用时间戳作为区块号
                        upload_status['block_number'] = original_record['timestamp']
                        print(f"使用时间戳作为区块号: {upload_status['block_number']}")
                except Exception as record_err:
                    print(f"获取原始记录信息失败: {str(record_err)}")
                    upload_status['block_number'] = 0  # 无法获取原始区块号
            else:
                # 其他错误
                upload_status['success'] = False
                upload_status['message'] = f"上链失败: {error_str}"
                upload_status['block_number'] = 0  # 不再使用临时区块号
        
        # 将上链结果添加到结果列表
        upload_results.append({
            'police_no': police_no,
            'success': upload_status['success'],
            'message': upload_status['message'],
            'is_duplicate': upload_status['is_duplicate'],
            'block_number': upload_status['block_number']
        })

        # 更新链数据以包含区块号和重复状态
        chain_data['is_duplicate'] = upload_status['is_duplicate']
        chain_data['BlockNumber'] = upload_status['block_number']
        chain_data['BlockNum'] = upload_status['block_number']
        
        # 只有当上链成功或非重复错误时才处理后续步骤
        if upload_status['success'] or not upload_status['is_duplicate']:
            # 更新元数据中的区块号，仅用于记录数据，不再添加到PDF中
            police_meta['BlockNum'] = upload_status['block_number']
            police_meta['BlockNumber'] = upload_status['block_number']
            
            # 简化为仅记录区块链信息
            if upload_status['success']:
                print(f"上链完成，区块号: {upload_status['block_number']}（保存在系统中，不显示在PDF中）")
                chain.blocks_list()  # 显示当前区块链中的区块信息
        else:
            # 对于重复记录，不再显示区块号和进行后续处理
            print(f"已跳过重复记录: {police_no}")

        chain_data_collection.append(chain_data)

        print(f"------ 第 {index+1} 条记录处理完成 ------\n")
    
    print(f"\n处理完成，共 {len(chain_data_collection)} 条记录")
    print("将上链数据保存到临时文件...")
    #将上链数据保存到临时文本文件,后续将保存到本地数据库便于查询
    with open(save_data_file, 'w', encoding='utf-8') as file:
        file.write(str(chain_data_collection))
    print(f"数据已保存到: {save_data_file}")
    
    # 将上链结果保存到结果文件
    results_file = save_data_file + ".results.json"
    try:
        with open(results_file, 'w', encoding='utf-8') as file:
            json.dump(upload_results, file, ensure_ascii=False, indent=2)
        print(f"上链结果已保存到: {results_file}")
    except Exception as e:
        print(f"保存上链结果时出错: {str(e)}")
    
    print("===== All_Police_Data_Upload_to_Chain函数执行完成 =====\n")

    # 返回处理结果，包含成功记录数和重复记录数
    success_count = sum(1 for r in upload_results if r['success'] and not r['is_duplicate'])
    duplicate_count = sum(1 for r in upload_results if r['is_duplicate'])
    error_count = sum(1 for r in upload_results if not r['success'])
    
    return {
        "total": len(chain_data_collection),
        "success": success_count,
        "duplicate": duplicate_count,
        "error": error_count,
        "results": upload_results  # 包含每条记录的详细结果
    } 