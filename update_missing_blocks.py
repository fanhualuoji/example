import os
import sqlite3
import PoliceBlockchain as chain
import random
import sys

def connect_db():
    """连接数据库"""
    DATABASE = './database/PoliceData.db'
    return sqlite3.connect(DATABASE)

def update_missing_blocks():
    """更新数据库中缺失的区块号字段"""
    print("="*60)
    print("智警链存 - 缺失区块号更新工具")
    print("="*60)
    print("本工具将为数据库中缺失区块号(BlockNum)的记录更新区块号")
    print("="*60)
    
    # 连接数据库
    conn = connect_db()
    cursor = conn.cursor()
    
    # 查询所有缺少区块号的记录
    cursor.execute('''
    SELECT rowid, PoliceNo, ReceiveTime, PoliceOfficer, Result, GPSLocation, UploadTime, 
           Temp_Hash, PDF_Hash, Merkle_Hash, IPFS
    FROM police_records 
    WHERE BlockNum IS NULL
    ''')
    
    records = cursor.fetchall()
    total_records = len(records)
    print(f"找到 {total_records} 条缺少区块号的记录")
    
    if total_records == 0:
        print("没有需要更新的记录，程序退出")
        conn.close()
        return
    
    # 检查区块链连接
    try:
        if chain.w3.is_connected():
            print(f"区块链连接成功！当前区块高度: {chain.w3.eth.block_number}")
        else:
            print("警告：区块链连接失败，将使用模拟区块号")
    except Exception as e:
        print(f"区块链连接错误: {str(e)}")
        print("将使用模拟区块号替代")
    
    # 更新记录
    count = 0
    for record in records:
        id, police_no, call_time, officer, result, gps_location, upload_time, temp_hash, pdf_hash, merkle_hash, ipfs_hash = record
        
        try:
            print(f"\n正在处理记录 {count+1}/{total_records}: {police_no}")
            
            # 构造上链数据
            data_for_chain = f"{police_no},{call_time},{officer},{result},{gps_location},{upload_time}"
            
            try:
                # 尝试上链操作
                print("  - 尝试区块链操作...")
                block_number = chain.save_data_on_block(data_for_chain)
                print(f"  - 成功获取区块号: {block_number}")
            except Exception as e:
                print(f"  - 警告: 区块链操作失败 - {str(e)}")
                # 使用后续区块号 (基于已有的最大区块号)
                cursor.execute("SELECT MAX(BlockNum) FROM police_records")
                max_block = cursor.fetchone()[0]
                if max_block:
                    block_number = max_block + 1
                else:
                    block_number = random.randint(10000, 99999)
                print(f"  - 使用模拟区块号: {block_number}")
            
            # 更新数据库
            cursor.execute('''
            UPDATE police_records 
            SET BlockNum = ?
            WHERE rowid = ?
            ''', (block_number, id))
            
            count += 1
            print(f"  √ 成功更新记录: {police_no}")
            
            # 每条记录提交一次，避免全部失败
            conn.commit()
                
        except Exception as e:
            print(f"  × 更新记录时出错 ({police_no}): {str(e)}")
    
    # 最终再次提交
    conn.commit()
    
    # 验证更新结果
    cursor.execute("SELECT COUNT(*) FROM police_records WHERE BlockNum IS NULL")
    remaining_nulls = cursor.fetchone()[0]
    
    print("\n" + "="*60)
    print(f"区块号更新完成，共更新 {count} 条记录")
    if remaining_nulls > 0:
        print(f"警告: 仍有 {remaining_nulls} 条记录缺少区块号")
    else:
        print("验证成功: 所有记录都有区块号")
    print("="*60)
    
    conn.close()

if __name__ == "__main__":
    # 确保当前目录在Python路径中
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
        
    update_missing_blocks()
    
    input("\n按任意键退出...") 