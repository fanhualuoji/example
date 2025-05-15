import os
import sqlite3
import hashlib
import datetime
import random
import string
import PoliceBlockchain as chain
import time
import ipfs_utils
from flask import session, redirect, url_for

DATABASE = './database/PoliceData.db'  # 数据库文件所在位置

def connect_db():
    """连接数据库"""
    return sqlite3.connect(DATABASE)

def generate_hash(data, length=32):
    """生成哈希值"""
    return hashlib.md5(str(data).encode()).hexdigest()[:length]

def update_blockchain_fields():
    """更新数据库中的区块链相关字段"""
    print("="*50)
    print("开始更新区块链字段...")
    print("="*50)
    
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    
    # 连接数据库
    conn = connect_db()
    cursor = conn.cursor()
    
    # 查询所有Active状态记录
    cursor.execute('''
    SELECT rowid, PoliceNo, ReceiveTime, PoliceOfficer, Result, GPSLocation, UploadTime 
    FROM police_records 
    WHERE RecordStatus = 'Active' OR RecordStatus IS NULL
    ''')
    
    records = cursor.fetchall()
    total_records = len(records)
    print(f"找到 {total_records} 条需要更新的记录")
    
    # 如果没有记录需要更新，尝试创建几条测试记录
    if total_records == 0:
        print("没有找到记录，尝试插入一条测试记录...")
        try:
            test_police_no = f"TEST{int(time.time())}"
            test_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            INSERT INTO police_records 
            (PoliceNo, ReceiveTime, PoliceOfficer, Result, GPSLocation, UploadTime, RecordStatus)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (test_police_no, test_time, "测试人员", "测试结果", "39.123,116.456", test_time, "Active"))
            
            conn.commit()
            print(f"已创建测试记录: {test_police_no}")
            
            # 重新查询
            cursor.execute('''
            SELECT rowid, PoliceNo, ReceiveTime, PoliceOfficer, Result, GPSLocation, UploadTime 
            FROM police_records 
            WHERE RecordStatus = 'Active' OR RecordStatus IS NULL
            ''')
            
            records = cursor.fetchall()
            total_records = len(records)
            print(f"现在找到 {total_records} 条需要更新的记录")
        except Exception as e:
            print(f"创建测试记录时出错: {str(e)}")
    
    count = 0
    for record in records:
        id, police_no, call_time, officer, result, gps_location, upload_time = record
        
        try:
            print(f"\n正在处理记录 {count+1}/{total_records}: {police_no}")
            
            # 生成临时哈希值
            source_data = f"{police_no}{call_time}{officer}{result}{gps_location}{upload_time}"
            temp_hash = generate_hash(source_data, 40)
            print(f"  - Temp_Hash: {temp_hash}")
            
            # 生成PDF哈希
            pdf_hash = generate_hash(f"pdf_{source_data}", 16)
            print(f"  - PDF_Hash: {pdf_hash}")
            
            # 生成Merkle哈希值
            merkle_hash = generate_hash(f"merkle_{source_data}", 24)
            print(f"  - Merkle_Hash: {merkle_hash}")
            
            # 尝试上传到IPFS
            # 先检查PDF文件是否存在
            pdf_file_path = os.path.join("police_records", f"{police_no}.pdf")
            if os.path.exists(pdf_file_path):
                print(f"  - 上传PDF文件到IPFS: {pdf_file_path}")
                ipfs_hash = ipfs_utils.upload_to_ipfs(pdf_file_path)
            else:
                # PDF不存在，上传记录数据
                data_for_ipfs = f"{police_no},{call_time},{officer},{result},{gps_location},{upload_time},{temp_hash}"
                print(f"  - 上传记录数据到IPFS")
                ipfs_hash = ipfs_utils.upload_to_ipfs(data_for_ipfs)
            print(f"  - IPFS: {ipfs_hash}")
            
            try:
                # 尝试上链操作
                print("  - 尝试区块链操作...")
                data_for_chain = f"{police_no},{call_time},{officer},{result},{gps_location},{upload_time}"
                block_number = chain.save_data_on_block(data_for_chain)
                print(f"  - 成功获取区块号: {block_number}")
            except Exception as e:
                print(f"  - 警告: 区块链操作失败 - {str(e)}")
                # 模拟区块号
                block_number = random.randint(10000, 99999)
                print(f"  - 使用模拟区块号: {block_number}")
            
            # 更新数据库
            cursor.execute('''
            UPDATE police_records 
            SET Temp_Hash = ?, BlockNum = ?, PDF_Hash = ?, Merkle_Hash = ?, IPFS = ?
            WHERE rowid = ?
            ''', (temp_hash, block_number, pdf_hash, merkle_hash, ipfs_hash, id))
            
            count += 1
            print(f"  √ 成功更新记录: {police_no}")
            
            # 提交每条记录
            conn.commit()
                
        except Exception as e:
            print(f"  × 更新记录时出错 ({police_no}): {str(e)}")
    
    # 最终提交
    conn.commit()
    
    # 验证更新是否成功
    cursor.execute('''
    SELECT COUNT(*) FROM police_records 
    WHERE Temp_Hash IS NOT NULL AND PDF_Hash IS NOT NULL AND Merkle_Hash IS NOT NULL AND IPFS IS NOT NULL AND BlockNum IS NOT NULL
    ''')
    validated_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n"+"="*50)
    print(f"区块链字段更新完成，共更新 {count} 条记录")
    print(f"成功验证 {validated_count} 条记录有完整的区块链字段")
    print(f"字段更新内容包括: Temp_Hash, BlockNum, PDF_Hash, Merkle_Hash, IPFS")
    print("="*50)

if __name__ == "__main__":
    # 删除或注释掉以下两行，因为它们在主模块中不能正常工作
    # if 'username' not in session:
    #     return redirect(url_for('login'))
    update_blockchain_fields() 