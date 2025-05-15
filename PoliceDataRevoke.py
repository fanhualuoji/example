import PoliceBlockchain as chain #导入预定义的区块链相关操作函数
import time
import sqlite3
import os

# 数据库文件路径
DATABASE = './database/PoliceData.db'

'''
数据库同步函数。
参数说明：
PoliceNo: 警情编号
Description: 撤销备注信息
'''
def SynToDatabase(PoliceNo, Description):
    # 确保数据库存在
    if not os.path.exists(DATABASE):
        raise Exception("数据库文件不存在")
    
    # 连接数据库
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    
    # 添加撤销记录到系统日志
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    cur.execute(
        "INSERT INTO operation_log (timestamp, action, username, details) VALUES (?, ?, ?, ?)",
        (current_time, "警情撤销", "admin", f"撤销警情记录 {PoliceNo}: {Description}")
    )
    
    # 更新警情记录状态
    sql_text = "UPDATE police_records SET RecordStatus='Revoked', Memo=? WHERE PoliceNo=?"
    cur.execute(sql_text, (Description, PoliceNo))
    
    # 提交并关闭连接
    con.commit()
    con.close()

'''
警情记录撤销的函数。
参数说明：
PoliceNo: 警情编号
Description: 撤销备注信息
'''
def Police_Record_Revoke(PoliceNo, Description): 
    revoke_date = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    
    # 构建待上链的数据
    chain_data = {
        'PoliceNo': PoliceNo,                 
        'Memo': Description,
        'RevokeDate': revoke_date
    } #警情记录撤销信息上链存证

    data = str(chain_data)
    
    try:
        # 数据上链存证,返回记录交易的区块号
        block_number = chain.save_data_on_block(data)    
        # 将区块号也加入备注信息
        description_with_block = Description + " 撤销记录区块号: " + str(block_number)
        # 同步写入数据库
        SynToDatabase(PoliceNo, description_with_block)
        # 显示当前区块链中的区块信息
        chain.blocks_list()
        
        return {
            'PoliceNo': PoliceNo,
            'RevokeDate': revoke_date,
            'BlockNumber': block_number,
            'Status': '成功'
        }
    except Exception as e:
        error_msg = f"撤销过程发生错误: {str(e)}"
        print(error_msg)
        
        # 记录错误日志但仍将撤销状态写入数据库
        try:
            SynToDatabase(PoliceNo, Description + " (上链失败，但状态已更改)")
        except Exception as db_error:
            print(f"数据库更新失败: {str(db_error)}")
        
        return {
            'PoliceNo': PoliceNo,
            'RevokeDate': revoke_date,
            'Status': '失败',
            'Error': error_msg
        } 