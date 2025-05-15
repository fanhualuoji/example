import os
import sys
from flask import Flask, redirect, url_for, render_template, g
from init_db import init_database
import datetime

# 创建应用实例
app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(
    DATABASE=os.path.join(app.root_path, 'database/PoliceData.db'),
    SECRET_KEY='PoliceChainSystem'
)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'upload')

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 检查是否为主要实例（避免Flask重新加载时重复执行）
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    # 初始化数据库
    init_database()
    
    # 在这里可以添加任何其他只需执行一次的初始化代码
    print("主应用程序实例已启动")

# 导入视图（必须在app创建后导入）
from views import *

# 时间戳格式化过滤器
@app.template_filter('datetime')
def format_datetime(timestamp):
    if isinstance(timestamp, int) or isinstance(timestamp, float):
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return timestamp

if __name__ == '__main__':
    app.run(debug=True) 