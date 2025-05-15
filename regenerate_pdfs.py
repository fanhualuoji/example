import os
import sqlite3
import sys

def connect_db():
    """连接数据库"""
    DATABASE = './database/PoliceData.db'
    return sqlite3.connect(DATABASE)

def regenerate_all_pdfs():
    """重新生成所有警情记录的PDF文件，确保包含区块链验证信息"""
    print("="*60)
    print("智警链存 - PDF文件重新生成工具")
    print("="*60)
    print("本工具将重新生成所有警情记录的PDF文件，确保包含区块链验证信息")
    print("="*60)
    
    # 确保当前目录在Python路径中
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    
    # 导入PDF生成模块
    try:
        from PoliceTemplatePDF import generate_pdf_from_record
        print("成功导入PDF生成模块")
    except ImportError as e:
        print(f"导入PDF模块时出错: {str(e)}")
        return
    
    # 连接数据库
    conn = connect_db()
    cursor = conn.cursor()
    
    # 查询所有记录
    cursor.execute('''
    SELECT * FROM police_records 
    ORDER BY PoliceNo
    ''')
    
    # 将结果转为字典列表
    column_names = [description[0] for description in cursor.description]
    records = []
    for row in cursor.fetchall():
        record = dict(zip(column_names, row))
        records.append(record)
    
    print(f"找到 {len(records)} 条警情记录")
    
    # 创建PDF输出目录
    pdf_dir = os.path.join(os.getcwd(), "police_records")
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
    
    # 重新生成所有PDF
    success_count = 0
    fail_count = 0
    
    for record in records:
        try:
            police_no = record['PoliceNo']
            
            # 检查区块链字段
            block_num = record.get('BlockNum')
            if block_num:
                print(f"处理记录 {police_no}, 区块号: {block_num}")
            else:
                print(f"处理记录 {police_no}, 未上链")
                
            # 生成PDF文件
            pdf_path = generate_pdf_from_record(record)
            success_count += 1
            print(f"  √ 成功生成PDF: {police_no}")
            
        except Exception as e:
            fail_count += 1
            print(f"  × 生成PDF时出错 ({record.get('PoliceNo', 'unknown')}): {str(e)}")
    
    # 关闭数据库连接
    conn.close()
    
    print("\n"+"="*60)
    print(f"PDF重新生成完成，共处理 {len(records)} 条记录")
    print(f"成功: {success_count}，失败: {fail_count}")
    print("="*60)

if __name__ == "__main__":
    regenerate_all_pdfs()
    
    input("\n按任意键退出...") 