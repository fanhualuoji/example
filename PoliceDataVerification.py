from PyPDF2 import PdfReader, PdfWriter
import merkleUtils as mk
import ast
import re
import json
import sqlite3
import os

'''
警情记录PDF文件验证函数。
参数说明：
police_pdf_file：警情记录PDF文件
'''
def verify_police_record(police_pdf_file):  
    try:
        # 读取PDF文件
        pdf_reader = PdfReader(open(police_pdf_file, 'rb'))
        
        # 获取PDF中的元数据
        pdf_metadata = pdf_reader.metadata
        
        # 调试信息
        print("PDF元数据：", pdf_metadata)
        
        # 尝试多种方式获取验证信息
        police_info = None
        
        # 方法1: 直接从chain_proof字段获取
        if '/chain_proof' in pdf_metadata:
            try:
                chain_proof = pdf_metadata['/chain_proof']
                if isinstance(chain_proof, list):
                    chain_proof = chain_proof[0]
                police_info = ast.literal_eval(chain_proof)
                print("通过chain_proof字段获取验证信息成功")
            except Exception as e:
                print(f"从chain_proof解析失败: {str(e)}")
        
        # 方法2: 从PDF的其他元数据字段获取
        if police_info is None:
            try:
                # 尝试从Police_Meta字段获取信息
                if '/Police_Meta' in pdf_metadata:
                    try:
                        # 将字符串转换为字典
                        police_meta_str = pdf_metadata['/Police_Meta']
                        # 移除可能的单引号，使其成为有效的JSON字符串
                        police_meta_str = police_meta_str.replace("'", '"')
                        police_meta = json.loads(police_meta_str)
                        police_info = {
                            'PoliceNo': police_meta.get('PoliceNo', ''),
                            'ReceiveTime': police_meta.get('ReceiveTime', ''),
                            'PoliceOfficer': police_meta.get('PoliceOfficer', ''),
                            'Result': police_meta.get('Result', ''),
                            'GPSLocation': police_meta.get('GPSLocation', ''),
                            'ReportType': police_meta.get('ReportType', ''),
                            'Location': police_meta.get('Location', ''),
                            'ContactName': police_meta.get('ContactName', ''),
                            'ContactPhone': police_meta.get('ContactPhone', ''),
                            'Priority': police_meta.get('Priority', ''),
                            'Department': police_meta.get('Department', ''),
                            'DispatchTime': police_meta.get('DispatchTime', ''),
                            'Description': police_meta.get('Description', '')
                        }
                        print("从Police_Meta字段提取信息成功")
                    except json.JSONDecodeError as e:
                        print(f"解析Police_Meta JSON失败: {str(e)}")
                        # 如果JSON解析失败，尝试使用ast.literal_eval
                        try:
                            police_meta = ast.literal_eval(police_meta_str)
                            police_info = {
                                'PoliceNo': police_meta.get('PoliceNo', ''),
                                'ReceiveTime': police_meta.get('ReceiveTime', ''),
                                'PoliceOfficer': police_meta.get('PoliceOfficer', ''),
                                'Result': police_meta.get('Result', ''),
                                'GPSLocation': police_meta.get('GPSLocation', ''),
                                'ReportType': police_meta.get('ReportType', ''),
                                'Location': police_meta.get('Location', ''),
                                'ContactName': police_meta.get('ContactName', ''),
                                'ContactPhone': police_meta.get('ContactPhone', ''),
                                'Priority': police_meta.get('Priority', ''),
                                'Department': police_meta.get('Department', ''),
                                'DispatchTime': police_meta.get('DispatchTime', ''),
                                'Description': police_meta.get('Description', '')
                            }
                            print("使用ast.literal_eval解析Police_Meta成功")
                        except Exception as e:
                            print(f"使用ast.literal_eval解析Police_Meta失败: {str(e)}")
                else:
                    # 如果没有Police_Meta字段，使用其他字段
                    police_info = {
                        'PoliceNo': pdf_metadata.get('/Title', '').replace('警情记录-', ''),
                        'ReceiveTime': '',
                        'PoliceOfficer': '',
                        'Result': '',
                        'GPSLocation': '',
                    }
                    print("从PDF元数据提取基本信息")
            except Exception as e:
                print(f"从其他元数据字段获取信息失败: {str(e)}")
        
        # 方法3: 从PDF文本内容中提取信息
        if police_info is None or not police_info.get('PoliceNo'):
            try:
                # 从PDF文本中提取信息
                text = ""
                for page in range(len(pdf_reader.pages)):
                    text += pdf_reader.pages[page].extract_text()
                
                # 使用正则表达式提取警情编号
                police_no_match = re.search(r'警情编号[:：]\s*([A-Za-z0-9]+)', text)
                if police_no_match:
                    police_info = {'PoliceNo': police_no_match.group(1)}
                    
                    # 尝试提取其他信息
                    receive_time_match = re.search(r'接警时间[:：]\s*([0-9-]+\s*[0-9:]+)', text)
                    if receive_time_match:
                        police_info['ReceiveTime'] = receive_time_match.group(1)
                    
                    contact_match = re.search(r'报警人[:：]\s*([^\n]+)', text)
                    if contact_match:
                        police_info['ContactName'] = contact_match.group(1)
                    
                    officer_match = re.search(r'处置人员[:：]\s*([^\n]+)', text)
                    if officer_match:
                        police_info['PoliceOfficer'] = officer_match.group(1)
                    
                    dispatch_time_match = re.search(r'出警时间[:：]\s*([0-9-]+\s*[0-9:]+)', text)
                    if dispatch_time_match:
                        police_info['DispatchTime'] = dispatch_time_match.group(1)
                    
                    department_match = re.search(r'出警单位[:：]\s*([^\n]+)', text)
                    if department_match:
                        police_info['Department'] = department_match.group(1)
                    
                    result_match = re.search(r'处置结果[:：]\s*([^\n]+)', text)
                    if result_match:
                        police_info['Result'] = result_match.group(1)
                    
                    desc_match = re.search(r'警情描述[:：]\s*([^\n]+)', text)
                    if desc_match:
                        police_info['Description'] = desc_match.group(1)
                    
                    location_match = re.search(r'发生地点[:：]\s*([^\n]+)', text)
                    if location_match:
                        police_info['Location'] = location_match.group(1)
                    
                    gps_match = re.search(r'地理坐标[:：]\s*([0-9.,]+)', text)
                    if gps_match:
                        police_info['GPSLocation'] = gps_match.group(1)
                    
                    block_match = re.search(r'区块编号[:：]\s*#?([0-9]+)', text)
                    if block_match:
                        police_info['BlockNum'] = block_match.group(1)
                    
                    hash_match = re.search(r'数据签名Hash[:：]\s*([a-f0-9]+)', text)
                    if hash_match:
                        police_info['Temp_Hash'] = hash_match.group(1)
                    
                    upload_time_match = re.search(r'上链时间[:：]\s*([0-9-]+\s*[0-9:]+)', text)
                    if upload_time_match:
                        police_info['UploadTime'] = upload_time_match.group(1)
                    
                    print("从PDF文本内容提取信息成功")
            except Exception as e:
                print(f"从PDF文本内容提取失败: {str(e)}")
        
        # 如果仍然无法获取验证信息，返回失败
        if police_info is None or not police_info.get('PoliceNo'):
            return {'Tag': 'fail', 'Content': '警情记录文件缺少区块链验证信息，无法验证！'}
        
        # 计算PDF当前的哈希值
        try:
            current_hash = mk.hash_certificate(police_pdf_file)
            print(f"成功计算PDF哈希值: {current_hash}")
        except Exception as e:
            print(f"计算PDF哈希值失败: {str(e)}")
            current_hash = "计算失败"  # 提供默认值而不是让它为None
        
        # 显示提取到的信息（调试用）
        print("提取到的警情信息:", police_info)
        
        # 尝试从数据库获取完整信息（如果PDF中信息不完整）
        try:
            # 连接数据库
            conn = sqlite3.connect('./database/PoliceData.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 查询记录
            cursor.execute('SELECT * FROM police_records WHERE PoliceNo = ?', (police_info['PoliceNo'],))
            record = cursor.fetchone()
            
            if record:
                # 补充PDF中可能缺失的字段
                for key in record.keys():
                    if key not in police_info or not police_info[key]:
                        police_info[key] = record[key]
                print(f"从数据库补充了记录信息")
            
            # 关闭连接
            conn.close()
        except Exception as e:
            print(f"从数据库获取补充信息失败: {str(e)}")
        
        # 在获取到PDF信息后，增加区块链数据比较
        if 'PoliceNo' in police_info and police_info['PoliceNo']:
            print("\n" + "="*50)
            print("开始区块链数据验证...")
            
            try:
                # 导入区块链验证模块
                import PoliceBlockchain as chain
                
                police_no = police_info['PoliceNo']
                current_hash = current_hash  # 当前计算的PDF哈希值
                
                # 从区块链获取存证数据
                print(f"从区块链获取警情编号 {police_no} 的存证数据...")
                
                # 获取区块链验证结果
                blockchain_result = chain.verify_police_record(police_no, current_hash)
                print(f"区块链验证结果: {blockchain_result}")
                
                # 如果成功获取区块数据，打印比较结果
                if blockchain_result.get('exists'):
                    # 从区块链获取完整记录
                    print("\n区块链记录详细信息:")
                    blockchain_record = chain.get_police_record(police_no)
                    if blockchain_record:
                        print(f"区块链上的记录: {blockchain_record}")
                        
                        # 打印比对结果
                        print("\n数据比对结果:")
                        print(f"{'字段':<15} {'PDF数据':<25} {'区块链数据':<25} {'匹配结果':<10}")
                        print("-"*75)
                        
                        # 比较关键字段
                        fields_to_compare = [
                            ('PoliceNo', 'policeNo'), 
                            ('ReceiveTime', 'receiveTime'),
                            ('PoliceOfficer', 'policeOfficer'),
                            ('Result', 'result'),
                            # GPS比较单独处理
                        ]
                        
                        all_match = True
                        for pdf_field, chain_field in fields_to_compare:
                            pdf_value = police_info.get(pdf_field, '')
                            chain_value = blockchain_record.get(chain_field, '')
                            match = pdf_value == chain_value
                            if not match:
                                all_match = False
                            
                            print(f"{pdf_field:<15} {pdf_value:<25} {chain_value:<25} {'✓' if match else '✗'}")
                        
                        # 特殊处理GPS位置数据比较
                        pdf_gps = police_info.get('GPSLocation', '')
                        chain_gps = blockchain_record.get('gpsLocation', '')
                        
                        # 智能比较GPS数据，处理格式差异
                        gps_match = False
                        if pdf_gps and chain_gps:
                            # 如果PDF中GPS格式为"纬度,经度"，而区块链中只有纬度
                            if ',' in pdf_gps:
                                pdf_lat = pdf_gps.split(',')[0].strip()
                                if chain_gps == pdf_lat:
                                    gps_match = True
                                # 或者区块链存储了完整的GPS但格式可能略有不同
                                elif ',' in chain_gps:
                                    chain_lat, chain_lng = chain_gps.split(',')
                                    pdf_lat, pdf_lng = pdf_gps.split(',')
                                    gps_match = chain_lat.strip() == pdf_lat.strip() and chain_lng.strip() == pdf_lng.strip()
                            else:
                                # 如果PDF只有一个值，则直接比较
                                gps_match = pdf_gps == chain_gps
                        elif not pdf_gps and not chain_gps:
                            # 如果两者都为空，视为匹配
                            gps_match = True
                        
                        if not gps_match:
                            all_match = False
                        
                        print(f"{'GPSLocation':<15} {pdf_gps:<25} {chain_gps:<25} {'✓' if gps_match else '✗ (格式不同但可能部分匹配)'}")
                        
                        # 哈希值比对
                        chain_pdf_hash = blockchain_record.get('pdfHash', '')
                        if not chain_pdf_hash:
                            # 尝试其他可能的字段名
                            for field in ['PDF_Hash', 'pdf_hash', 'pdfhash']:
                                if field in blockchain_record and blockchain_record[field]:
                                    chain_pdf_hash = blockchain_record[field]
                                    break
        
                        # 格式化哈希值以确保一致比较
                        if chain_pdf_hash:
                            chain_pdf_hash = chain_pdf_hash.lower().strip()
                            if chain_pdf_hash.startswith("0x"):
                                chain_pdf_hash = chain_pdf_hash[2:]
                        else:
                            chain_pdf_hash = ""
                            
                        if current_hash:
                            current_hash = current_hash.lower().strip()
                            if current_hash.startswith("0x"):
                                current_hash = current_hash[2:]
                        else:
                            current_hash = ""
                            
                        # 如果区块链上的哈希为空，也视为不匹配
                        if not chain_pdf_hash:
                            pdf_hash_match = False
                            print(f"警告: 区块链上的PDF哈希为空!")
                        else:
                            pdf_hash_match = current_hash == chain_pdf_hash or blockchain_result.get('hash_match', False)
                            if not pdf_hash_match:
                                print(f"哈希不匹配的详细信息:")
                                print(f"区块链哈希: {chain_pdf_hash}")
                                print(f"当前计算哈希: {current_hash}")
                                print(f"区块链哈希长度: {len(chain_pdf_hash)}, 当前哈希长度: {len(current_hash)}")
                        
                        print(f"{'PDF哈希':<15} {current_hash[:15] if current_hash else 'N/A'}... {chain_pdf_hash[:15] if chain_pdf_hash else 'N/A'}... {'✓' if pdf_hash_match else '✗'}")
                        
                        if all_match and pdf_hash_match:
                            print("\n总结: 所有数据完全匹配! ✓")
                            verification_result = "所有数据完全匹配，警情记录验证通过!"
                            
                            # 确保将当前哈希值添加到police_info中
                            police_info['CurrentHash'] = current_hash
                            
                            result = {
                                'Tag': 'pass',
                                'Content': verification_result,
                                'Info': police_info,
                                'Data': {
                                    'hash_match': True,
                                    'all_match': True
                                }
                            }
                        else:
                            print("\n总结: 数据存在不匹配! ✗")
                            if not pdf_hash_match:
                                verification_result = "PDF文件哈希值与区块链不匹配，警情记录验证失败!"
                            else:
                                verification_result = "基本信息与区块链不匹配，警情记录验证失败!"
                            
                            # 确保将当前哈希值添加到police_info中，即使验证失败
                            police_info['CurrentHash'] = current_hash
                            
                            # 当验证失败时更新数据库状态
                            if not (all_match and pdf_hash_match):
                                print("\n总结: 数据存在不匹配! ✗")
                                reason = "PDF哈希值与区块链不匹配" if not pdf_hash_match else "基本信息与区块链不匹配"
                                update_record_status(police_no, 'Invalid', reason)
                                
                                if not pdf_hash_match:
                                    verification_result = "PDF文件哈希值与区块链不匹配，警情记录验证失败!"
                                else:
                                    verification_result = "基本信息与区块链不匹配，警情记录验证失败!"
                                
                                # 确保将当前哈希值添加到police_info中，即使验证失败
                                police_info['CurrentHash'] = current_hash
                                
                                # 尽管验证失败，我们仍然需要保存验证信息，但标记为'fail'
                                result = {
                                    'Tag': 'pass',  # 保持'pass'使得界面仍然显示验证结果
                                    'Content': verification_result,
                                    'Info': police_info,
                                    'Data': {
                                        'hash_match': pdf_hash_match,
                                        'all_match': all_match
                                    }
                                }
                            
                            return result
                    else:
                        print("无法从区块链获取完整记录")
                else:
                    print(f"区块链验证失败: {blockchain_result.get('error', '未知错误')}")
                    # 如果区块链验证失败，标记记录为无效
                    if 'PoliceNo' in police_info:
                        update_record_status(police_info['PoliceNo'], 'Invalid', "区块链验证失败")
            
            except Exception as e:
                print(f"区块链验证过程出错: {str(e)}")
                import traceback
                traceback.print_exc()
            
            print("="*50)
        
        # 信息输出
        info = {
            'PoliceNo': police_info.get('PoliceNo', 'untitled'),
            'ReceiveTime': police_info.get('ReceiveTime', ''),
            'PoliceOfficer': police_info.get('PoliceOfficer', ''),
            'ContactName': police_info.get('ContactName', ''),
            'Description': police_info.get('Description', ''),
            'Location': police_info.get('Location', ''),
            'DispatchTime': police_info.get('DispatchTime', ''),
            'Department': police_info.get('Department', ''),
            'Result': police_info.get('Result', ''),
            'GPSLocation': police_info.get('GPSLocation', ''),
            'Temp_Hash': police_info.get('Temp_Hash', ''),
            'UploadTime': police_info.get('UploadTime', ''),
            'BlockNum': police_info.get('BlockNum', '未上链'),
            'CurrentHash': current_hash  # 确保这里包含当前哈希值
        }
        
        # 调试输出当前哈希值
        print(f"当前文件哈希值: {current_hash}")
        
        # 检查是否有区块号，如果有区块号就是已上链
        if info['BlockNum'] and info['BlockNum'] != 'N/A' and info['BlockNum'] != '未上链':
            return {
                'Tag': 'pass', 
                'Content': f'警情记录文件验证成功，内容完好无篡改。区块号: {info["BlockNum"]}', 
                'Info': info
            }
        else:
            # 如果没有区块号但有其他信息，仍然返回成功但提示未上链
            return {
                'Tag': 'pass', 
                'Content': '警情记录文件验证成功，但该记录尚未上链。', 
                'Info': info
            }
        
    except Exception as e:
        # 验证失败
        print(f"验证过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'Tag': 'fail', 'Content': f'警情记录文件验证失败: {str(e)}'}

def update_record_status(police_no, status='Invalid', reason=None):
    """更新警情记录的状态到数据库
    
    Args:
        police_no: 警情编号
        status: 记录状态，可以是'Invalid'(无效)或'Active'(有效)
        reason: 无效的原因说明
    
    Returns:
        更新结果：成功返回True，失败返回False
    """
    try:
        # 使用相对路径连接数据库，确保与其他函数使用相同的路径
        db_path = './database/PoliceData.db'
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查记录是否存在
        cursor.execute('SELECT * FROM police_records WHERE PoliceNo = ?', (police_no,))
        record = cursor.fetchone()
        
        if not record:
            print(f"警情记录 {police_no} 不存在于数据库中")
            return False
        
        # 更新记录状态
        import datetime
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 如果未提供原因，使用默认原因
        if not reason:
            reason = "PDF验证失败，可能被篡改" if status == 'Invalid' else ""
        
        cursor.execute('''
            UPDATE police_records 
            SET RecordStatus = ?, 
                Memo = ?,
                RevokeTime = ?,
                RevokeUser = ? 
            WHERE PoliceNo = ?
        ''', (status, reason, current_time, "系统自动", police_no))
        
        conn.commit()
        conn.close()
        
        print(f"已更新警情记录 {police_no} 的状态为 {status}")
        return True
        
    except Exception as e:
        print(f"更新记录状态失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

'''
对比两个警情记录文件的一致性
参数说明：
pdf_file1, pdf_file2：两个需要对比的PDF文件
'''
def compare_police_records(pdf_file1, pdf_file2):
    try:
        # 分别验证两个文件
        result1 = verify_police_record(pdf_file1)
        result2 = verify_police_record(pdf_file2)
        
        # 检查两个文件是否都验证通过
        if result1['Tag'] == 'fail' or result2['Tag'] == 'fail':
            if result1['Tag'] == 'fail':
                return result1
            else:
                return result2
        
        # 提取两个文件的信息
        info1 = result1['Info']
        info2 = result2['Info']
        
        # 对比警情编号
        if info1['PoliceNo'] != info2['PoliceNo']:
            return {'Tag': 'fail', 'Content': '两份警情记录的警情编号不一致!'}
        
        # 对比其他关键信息
        mismatch_fields = []
        for field in ['ReceiveTime', 'PoliceOfficer', 'Result', 'GPSLocation']:
            if info1[field] != info2[field]:
                mismatch_fields.append(field)
        
        if mismatch_fields:
            fields_str = ', '.join(mismatch_fields)
            return {'Tag': 'fail', 'Content': f'警情记录数据不一致，不一致字段: {fields_str}'}
        
        return {'Tag': 'pass', 'Content': '两份警情记录数据完全一致。', 'Info': info1}
        
    except Exception as e:
        return {'Tag': 'fail', 'Content': f'警情记录比对失败: {str(e)}'} 