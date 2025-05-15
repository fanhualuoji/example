-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    last_login TEXT
);

-- 警情记录表
CREATE TABLE IF NOT EXISTS police_records (
    PoliceNo TEXT PRIMARY KEY,
    ReceiveTime TEXT,
    PoliceOfficer TEXT,
    Result TEXT,
    GPSLocation TEXT,
    UploadTime TEXT,
    RecordStatus TEXT DEFAULT 'Active',
    RevokeReason TEXT,
    RevokeTime TEXT,
    RevokeUser TEXT,
    Temp_Hash TEXT,
    BlockNum INTEGER,
    PDF_Hash TEXT,
    Merkle_Hash TEXT,
    IPFS TEXT,
    ReportType TEXT,
    Location TEXT,
    ContactName TEXT,
    ContactPhone TEXT,
    Priority TEXT DEFAULT '普通',
    Department TEXT
);

-- 系统日志表
CREATE TABLE IF NOT EXISTS operation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    username TEXT,
    details TEXT
); 