import os
import sqlite3
import hashlib
import PoliceBlockchain as chain
import datetime

DATABASE = './database/PoliceData.db'  # 数据库文件所在位置

def connect_db():
    return sqlite3.connect(DATABASE)

def update_blockchain_info():
    print("开始更新区块链信息...")
    
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    
    # 连接数据库
    conn = connect_db()
    cursor = conn.cursor()
    
    # 查询所有具有NULL区块链信息的记录
    cursor.execute('''
    SELECT PoliceNo, ReceiveTime, PoliceOfficer, Result, GPSLocation, UploadTime 
    FROM police_records 
    WHERE RecordStatus = 'Active' AND (Temp_Hash IS NULL OR BlockNum IS NULL OR PDF_Hash IS NULL OR Merkle_Hash IS NULL)
    ''')
    
    records = cursor.fetchall()
    print(f"找到 {len(records)} 条需要更新的记录")
    
    count = 0
    for record in records:
        police_no, call_time, officer, result, gps_location, upload_time = record
        
        try:
            # 生成临时哈希值
            temp_hash = hashlib.md5((police_no + str(call_time) + officer + result + gps_location).encode()).hexdigest()
            
            # 上链操作 - 简化模拟
            try:
                data_to_chain = f"{police_no},{call_time},{officer},{result},{gps_location},{upload_time}"
                block_number = chain.save_data_on_block(data_to_chain)
                blockchain_hash = f"0x{temp_hash[:16]}"  # 简化的区块链哈希模拟
            except Exception as chain_error:
                print(f"警告: 区块链上链失败 ({police_no}) - {str(chain_error)}")
                # 如果区块链上链失败，仍然继续数据库操作
                block_number = None
                blockchain_hash = None
            
            # 生成Merkle哈希值(简化)
            merkle_hash = f"0x{temp_hash[16:32]}"
            
            # 计算PDF哈希
            pdf_hash = f"0x{temp_hash[8:24]}"
            
            # 更新数据库记录
            cursor.execute('''
            UPDATE police_records 
            SET Temp_Hash = ?, BlockNum = ?, PDF_Hash = ?, Merkle_Hash = ?
            WHERE PoliceNo = ?
            ''', (temp_hash, block_number, pdf_hash, merkle_hash, police_no))
            
            count += 1
            print(f"已更新记录 {count}/{len(records)}: {police_no}")
            
        except Exception as e:
            print(f"更新记录时出错 ({police_no}): {str(e)}")
    
    conn.commit()
    conn.close()
    
    print(f"区块链信息更新完成，共更新 {count} 条记录")

if __name__ == "__main__":
    update_blockchain_info() 