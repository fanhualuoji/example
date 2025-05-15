#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 用于快速启动警情链系统和数据可视化模块
"""

import os
import sys
import argparse
import webbrowser
import subprocess
import time
from threading import Thread

def check_requirements():
    """检查依赖是否已安装"""
    try:
        import flask
        import web3
        import reportlab
        import pandas
        return True
    except ImportError as e:
        print(f"缺少必要依赖: {e}")
        print("请先安装依赖: pip install -r requirements.txt")
        return False

def init_system():
    """初始化系统，包括数据库和示例数据"""
    print("正在初始化系统...")
    
    # 初始化数据库
    import init_db
    init_db.init_database()
    
    # 添加示例数据（如果需要）
    try:
        if hasattr(init_db, 'add_sample_data'):
            init_db.add_sample_data()
            print("已添加示例数据用于测试")
    except Exception as e:
        print(f"添加示例数据时出错: {str(e)}")
    
    # 部署智能合约（如果需要）
    try:
        print("正在检查智能合约...")
        contract_file = os.path.join('contracts', 'contract_addresses.json')
        if not os.path.exists(contract_file):
            print("智能合约尚未部署，正在部署...")
            subprocess.run([sys.executable, 'deploy_contracts.py'], check=True)
        else:
            print("智能合约已部署")
    except Exception as e:
        print(f"部署智能合约时出错: {str(e)}")
        print("请手动运行: python deploy_contracts.py")

def open_browser(url, delay=2):
    """延迟一段时间后打开浏览器"""
    def _open_browser():
        time.sleep(delay)
        webbrowser.open(url)
    
    Thread(target=_open_browser).start()

def start_app(open_browser_flag=True, port=5000):
    """启动Flask应用"""
    if open_browser_flag:
        open_browser(f"http://localhost:{port}", delay=2)
    
    # 启动应用
    from app import app
    app.run(host='0.0.0.0', port=port, debug=True)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="警情链区块链系统启动脚本")
    parser.add_argument('--init', action='store_true', help='初始化系统（包括数据库和示例数据）')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--port', type=int, default=5000, help='指定运行端口（默认5000）')
    
    args = parser.parse_args()
    
    # 检查依赖
    if not check_requirements():
        return
    
    # 初始化系统（如果需要）
    if args.init:
        init_system()
    
    # 启动应用
    print(f"正在启动警情链系统，访问地址: http://localhost:{args.port}")
    print(f"数据可视化大屏地址: http://localhost:{args.port}/data_view/demo")
    start_app(not args.no_browser, args.port)

if __name__ == "__main__":
    main() 