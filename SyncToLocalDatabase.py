import sqlite3
import os
import time

# 数据库文件路径
DATABASE = './database/PoliceData.db'

'''
将警情数据上链后的信息同步到本地数据库
参数说明：
data_to_load: 上链后的数据文件路径
'''
def sync_to_database(data_to_load):
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    
    # 连接到数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 打开并读取文件内容
    with open(data_to_load, 'r', encoding='utf-8') as file:
        data = file.read()  # 读取文件内容
        data = eval(data)  # 将文本内容还原成list

    # 添加操作日志
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    cursor.execute(
        "INSERT INTO operation_log (timestamp, action, username, details) VALUES (?, ?, ?, ?)",
        (current_time, "数据同步", "系统", f"从{data_to_load}同步{len(data)}条警情记录")
    )
    
    # 遍历 list 中所有数据并插入数据库
    inserted_count = 0
    updated_count = 0
    
    for item in data:
        # 使用参数化查询来避免 SQL 注入
        sql_text = """
        INSERT INTO police_records (
            PoliceNo, ReceiveTime, PoliceOfficer, Result, GPSLocation, 
            Temp_Hash, PDF_Hash, Merkle_Hash, IPFS, BlockNumber, UploadTime, RecordStatus, Memo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # 将数据作为元组传递给 execute 方法
        data_to_insert = (
            item['PoliceNo'],
            item['ReceiveTime'],
            item['PoliceOfficer'],
            item['Result'],
            item['GPSLocation'],
            item['Temp_Hash'],
            item['PDF_Hash'],
            str(item['Merkel_Tophash']),  # 确保 Merkel_Tophash 是字符串
            item['IPFS'],
            item['BlockNumber'],
            item['UploadTime'],
            'Active',  # 设置初始状态为活跃
            'N/A'      # 初始备注为N/A
        )

        try:
            cursor.execute(sql_text, data_to_insert)
            inserted_count += 1
        except sqlite3.IntegrityError:
            # 如果记录已存在，则更新它
            update_sql = """
            UPDATE police_records SET
                ReceiveTime=?, PoliceOfficer=?, Result=?, GPSLocation=?,
                Temp_Hash=?, PDF_Hash=?, Merkle_Hash=?, IPFS=?, BlockNumber=?,
                UploadTime=?
            WHERE PoliceNo=?
            """
            
            cursor.execute(update_sql, (
                item['ReceiveTime'],
                item['PoliceOfficer'],
                item['Result'],
                item['GPSLocation'],
                item['Temp_Hash'],
                item['PDF_Hash'],
                str(item['Merkel_Tophash']),
                item['IPFS'],
                item['BlockNumber'],
                item['UploadTime'],
                item['PoliceNo']
            ))
            updated_count += 1

    # 添加操作结果到日志
    cursor.execute(
        "INSERT INTO operation_log (timestamp, action, username, details) VALUES (?, ?, ?, ?)",
        (current_time, "同步结果", "系统", f"新增{inserted_count}条，更新{updated_count}条")
    )
    
    # 提交事务并关闭数据库连接
    conn.commit()
    conn.close()
    
    print(f"数据同步完成！新增{inserted_count}条，更新{updated_count}条")
    return len(data) 