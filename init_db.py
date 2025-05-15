import os
import sqlite3
import datetime

# 数据库文件路径
DB_PATH = './database/PoliceData.db'

def init_database():
    """初始化数据库"""
    print("开始初始化数据库...")
    
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建警情记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS police_records (
        PoliceNo TEXT PRIMARY KEY,
        ReceiveTime TEXT,
        PoliceOfficer TEXT,
        Result TEXT,
        GPSLocation TEXT,
        Temp_Hash TEXT,
        PDF_Hash TEXT,
        Merkle_Hash TEXT,
        IPFS TEXT,
        UploadTime TEXT,
        RecordStatus TEXT DEFAULT 'Active',
        Memo TEXT DEFAULT 'N/A',
        BlockNum INTEGER,
        RevokeTime TEXT,
        RevokeUser TEXT,
        Status TEXT,
        ReportTime TEXT,
        Location TEXT, 
        ContactName TEXT,
        ContactPhone TEXT,
        Department TEXT,
        Description TEXT
    )
    ''')
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        created_at TEXT
    )
    ''')
    
    # 添加操作日志表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS operation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        action TEXT NOT NULL,
        username TEXT,
        details TEXT
    )
    ''')
    
    # 提交更改
    conn.commit()
    
    # 检查是否已存在管理员账户
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        # 创建默认管理员账户
        from werkzeug.security import generate_password_hash
        admin_password = generate_password_hash('admin123')
        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        INSERT INTO users (username, password, role, created_at)
        VALUES (?, ?, ?, ?)
        ''', ('admin', admin_password, 'admin', created_at))
        
        conn.commit()
        print("已创建默认管理员账户: admin/admin123")
    
    # 关闭连接
    conn.close()
    
    print("数据库初始化完成!")

def add_sample_data():
    """添加示例数据用于测试数据可视化模块"""
    import random
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查是否已有足够数据
    cursor.execute("SELECT COUNT(*) FROM police_records")
    count = cursor.fetchone()[0]
    
    if count >= 50:  # 如果已有足够数据，则跳过
        print(f"数据库中已有{count}条记录，无需添加示例数据")
        conn.close()
        return
    
    # 示例数据
    areas = ['北京市', '上海市', '广州市', '深圳市', '杭州市', '南京市', '重庆市', '武汉市', '西安市', '成都市']
    statuses = ['Active', 'Revoked']
    results = ['警情已处理', '警情待处理', '警情处理中', '警情已解决', '警情需跟进', '警情已撤销', '警情转办']
    departments = ['刑侦大队', '交警大队', '治安大队', '巡警大队', '网安大队', '特警大队']
    
    # 生成过去30天的随机日期
    now = datetime.now()
    
    # 生成示例数据
    print("正在生成示例数据...")
    for i in range(1, 101):
        police_no = f"P{now.year}{now.month:02d}{i:04d}"
        
        # 随机日期在过去30天内
        random_days = random.randint(0, 30)
        record_date = now - timedelta(days=random_days)
        receive_time = record_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # 随机上传时间（在接收时间之后的24小时内）
        upload_hours = random.randint(1, 24)
        upload_time = (record_date + timedelta(hours=upload_hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 随机区域和GPS位置
        area = random.choice(areas)
        lat = random.uniform(30.0, 40.0)
        lng = random.uniform(110.0, 120.0)
        gps_location = f"{area},{lat:.6f},{lng:.6f}"
        
        # 随机生成其他字段
        officer = f"警员{random.randint(1001, 9999)}"
        result = random.choice(results)
        status = random.choice(statuses)
        department = random.choice(departments)
        
        # 随机生成哈希值
        temp_hash = ''.join(random.choices('0123456789abcdef', k=64))
        pdf_hash = ''.join(random.choices('0123456789abcdef', k=64))
        merkle_hash = ''.join(random.choices('0123456789abcdef', k=64))
        ipfs_hash = f"ipfs://Qm{''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyzABCDEF', k=44))}"
        
        # 50%的概率有区块号（已上链）
        block_num = random.randint(100000, 999999) if random.random() > 0.5 else None
        
        # 撤销相关信息（只有状态为Revoked的才有）
        revoke_time = None
        revoke_user = None
        if status == 'Revoked':
            revoke_hours = random.randint(25, 72)
            revoke_time = (record_date + timedelta(hours=revoke_hours)).strftime('%Y-%m-%d %H:%M:%S')
            revoke_user = 'admin'
        
        # 插入到数据库
        try:
            cursor.execute('''
            INSERT INTO police_records 
            (PoliceNo, ReceiveTime, PoliceOfficer, Result, GPSLocation, 
             Temp_Hash, PDF_Hash, Merkle_Hash, IPFS, UploadTime, 
             RecordStatus, BlockNum, RevokeTime, RevokeUser, Department)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                police_no, 
                receive_time,
                officer, 
                result,
                gps_location,
                temp_hash,
                pdf_hash,
                merkle_hash,
                ipfs_hash,
                upload_time,
                status,
                block_num,
                revoke_time,
                revoke_user,
                department
            ))
        except sqlite3.IntegrityError:
            # 如警情编号重复，则跳过
            continue
    
    conn.commit()
    
    # 获取实际插入的记录数
    cursor.execute("SELECT COUNT(*) FROM police_records")
    new_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"已添加示例数据，当前共有{new_count}条记录")

if __name__ == "__main__":
    init_database()
    # 如果需要添加示例数据，取消下面一行的注释
    # add_sample_data() 