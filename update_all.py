import os
import sys
import time

print("="*60)
print("智警链存 - 区块链字段更新工具")
print("="*60)
print("本工具将帮助您更新数据库中的区块链相关字段")
print("包括: Temp_Hash, BlockNum, PDF_Hash, Merkle_Hash, IPFS")
print("="*60)

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    # 1. 检查数据库结构
    print("\n步骤1: 更新数据库结构...")
    from update_database_structure import update_database_structure
    update_database_structure()
    print("数据库结构检查完成！")
    
    # 2. 更新区块链字段
    print("\n步骤2: 更新区块链字段...")
    from update_blockchain_fields import update_blockchain_fields
    update_blockchain_fields()
    print("区块链字段更新完成！")
    
    # 3. 生成PDF文件
    print("\n步骤3: 更新PDF文件...")
    import sqlite3
    try:
        # 尝试导入PoliceTemplatePDF模块
        from PoliceTemplatePDF import generate_pdf_from_record, generate_hash
        print("成功导入PDF生成模块")
    except ImportError as e:
        print(f"导入PDF模块时出错: {str(e)}")
        print("尝试使用相对导入...")
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("PoliceTemplatePDF", 
                                                        os.path.join(current_dir, "PoliceTemplatePDF.py"))
            PoliceTemplatePDF = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(PoliceTemplatePDF)
            generate_pdf_from_record = PoliceTemplatePDF.generate_pdf_from_record
            generate_hash = PoliceTemplatePDF.generate_hash
            print("成功通过备用方式导入PDF生成模块")
        except Exception as e2:
            print(f"备用导入方式也失败: {str(e2)}")
            print("跳过PDF生成步骤")
            raise
    
    # 数据库连接
    DATABASE = './database/PoliceData.db'
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有有区块链字段的记录
    cursor.execute('''
    SELECT * FROM police_records 
    WHERE Temp_Hash IS NOT NULL AND PDF_Hash IS NOT NULL AND RecordStatus='Active'
    ''')
    
    records = cursor.fetchall()
    print(f"找到 {len(records)} 条记录需要生成PDF")
    
    # 创建PDF目录
    pdf_dir = os.path.join(os.getcwd(), "police_records")
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
    
    # 生成PDF
    count = 0
    for record in records:
        try:
            record_dict = dict(record)
            police_no = record_dict.get('PoliceNo')
            pdf_path = generate_pdf_from_record(record_dict)
            count += 1
            print(f"√ 成功生成PDF: {police_no}")
        except Exception as e:
            print(f"× 生成PDF时出错 ({police_no}): {str(e)}")
    
    conn.close()
    print(f"PDF更新完成，共生成 {count} 个PDF文件")
    
    print("\n"+"="*60)
    print("所有更新完成！现在您的数据库和PDF文件已更新，系统应可正常工作")
    print("="*60)

except Exception as e:
    print(f"\n错误: {str(e)}")
    print("更新过程中断，请检查错误信息")

input("\n按任意键退出...") 