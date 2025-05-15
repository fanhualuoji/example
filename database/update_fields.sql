-- 添加新的非必须字段到police_records表
ALTER TABLE police_records ADD COLUMN ReportType TEXT;
ALTER TABLE police_records ADD COLUMN Location TEXT;
ALTER TABLE police_records ADD COLUMN ContactName TEXT;
ALTER TABLE police_records ADD COLUMN ContactPhone TEXT;
ALTER TABLE police_records ADD COLUMN Priority TEXT DEFAULT '普通';
ALTER TABLE police_records ADD COLUMN Department TEXT;

-- 添加出警时间和警情描述字段
ALTER TABLE police_records ADD COLUMN DispatchTime TEXT;
ALTER TABLE police_records ADD COLUMN Description TEXT;

-- 更新状态
UPDATE police_records SET RecordStatus = 'Active' WHERE RecordStatus IS NULL;

-- 确认更新成功
.schema police_records 