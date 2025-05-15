import os
import sqlite3
import sys

def connect_db():
    """连接数据库"""
    DATABASE = './database/PoliceData.db'
    return sqlite3.connect(DATABASE)

def remove_duplicate_column():
    """删除数据库中重复的BlockNumber列，保留BlockNum列"""
    print("="*60)
    print("智警链存 - 数据库结构优化工具")
    print("="*60)
    print("本工具将删除police_records表中重复的BlockNumber字段，保留BlockNum字段")
    print("="*60)
    
    # 连接数据库
    conn = connect_db()
    cursor = conn.cursor()
    
    # 获取表结构
    cursor.execute("PRAGMA table_info(police_records)")
    columns = cursor.fetchall()
    
    print("当前表结构:")
    for col in columns:
        print(f"{col[0]}. {col[1]} ({col[2]})")
    
    # 检查BlockNumber列是否存在
    has_blockNumber = any(col[1] == 'BlockNumber' for col in columns)
    
    if not has_blockNumber:
        print("\n表中不存在BlockNumber列，无需进行操作。")
        conn.close()
        return
    
    try:
        # 步骤1: 创建新表结构SQL语句
        print("\n步骤1: 准备创建新表结构，不包含重复的BlockNumber字段...")
        
        # 获取所有要保留的列
        columns_to_keep = []
        for col in columns:
            if col[1] != 'BlockNumber':
                columns_to_keep.append(col)
        
        # 构建新表的创建语句
        create_table_sql = "CREATE TABLE police_records_new (\n"
        for i, col in enumerate(columns_to_keep):
            col_name = col[1]
            col_type = col[2]
            not_null = "NOT NULL" if col[3] == 1 else ""
            default_val = f"DEFAULT {col[4]}" if col[4] is not None else ""
            pk = "PRIMARY KEY" if col[5] == 1 else ""
            
            create_table_sql += f"    {col_name} {col_type} {not_null} {default_val} {pk}".strip()
            if i < len(columns_to_keep) - 1:
                create_table_sql += ","
            create_table_sql += "\n"
        create_table_sql += ")"
        
        print("新表创建SQL:")
        print(create_table_sql)
        
        # 步骤2: 执行建表语句
        print("\n步骤2: 创建新表...")
        cursor.execute(create_table_sql)
        
        # 步骤3: 准备并执行数据复制
        print("步骤3: 复制数据到新表...")
        
        # 构建列名列表（排除BlockNumber）
        column_names = [col[1] for col in columns_to_keep]
        
        # 构建INSERT语句
        insert_sql = f"""
        INSERT INTO police_records_new ({', '.join(column_names)})
        SELECT {', '.join(column_names)} FROM police_records
        """
        
        print("数据复制SQL:")
        print(insert_sql)
        
        # 执行数据复制
        cursor.execute(insert_sql)
        
        # 统计并验证记录数量
        cursor.execute("SELECT COUNT(*) FROM police_records")
        old_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM police_records_new")
        new_count = cursor.fetchone()[0]
        
        print(f"原表记录数: {old_count}")
        print(f"新表记录数: {new_count}")
        
        if old_count != new_count:
            print("警告: 记录数不匹配，操作已取消")
            conn.rollback()
            conn.close()
            return
        
        # 步骤4: 替换旧表
        print("步骤4: 删除旧表并重命名新表...")
        cursor.execute("DROP TABLE police_records")
        cursor.execute("ALTER TABLE police_records_new RENAME TO police_records")
        
        # 提交更改
        conn.commit()
        
        # 验证最终结构
        cursor.execute("PRAGMA table_info(police_records)")
        final_columns = cursor.fetchall()
        
        print("\n更新后的表结构:")
        for col in final_columns:
            print(f"{col[0]}. {col[1]} ({col[2]})")
        
        has_blockNumber_after = any(col[1] == 'BlockNumber' for col in final_columns)
        if not has_blockNumber_after:
            print("\n成功: BlockNumber列已被删除")
            
        print("\n" + "="*60)
        print("数据库结构优化完成！已删除重复的BlockNumber字段，保留BlockNum字段")
        print("="*60)
    
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("操作失败，已回滚所有更改")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    # 确保当前目录在Python路径中
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
        
    remove_duplicate_column()
    
    input("\n按任意键退出...") 