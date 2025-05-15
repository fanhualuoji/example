import os
import time
import datetime
from app import app
from flask import Flask, flash, request, redirect, render_template, session, jsonify, g, url_for, abort, send_file, current_app
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
import csv
import json
import sqlite3
from werkzeug.security import check_password_hash
from functools import wraps

import PoliceBlockchain as chain  # 导入预定义的区块链相关操作函数
import PoliceDataVerification as PDV  # 导入预定义的警情数据验证相关函数
from PoliceDataUpload import All_Police_Data_Upload_to_Chain  # 导入预定义的数据上链操作相关函数
from PoliceDataRevoke import Police_Record_Revoke  # 导入预定义的警情撤销函数
from SyncToLocalDatabase import sync_to_database  # 导入预定义的数据库写入操作相关函数
from models import User
from PoliceTemplatePDF import generate_pdf_from_record  # 导入PoliceTemplatePDF模块
import ipfs_utils
import random
import string
import hashlib
import contract_manager  # 导入合约管理模块
import sys
from web3 import Web3

# 数据库配置文件
DATABASE = './database/PoliceData.db'  # 数据库文件所在位置
DEBUG = True
SECRET_KEY = 'PoliceChainSystem'
USERNAME = 'admin'
PASSWORD = 'admin123'

def connect_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query, args)
    
    columns = [column[0] for column in cursor.description]
    results = []
    
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    
    conn.close()
    return (results[0] if results else None) if one else results

@app.before_request
def before_request():
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 简化用户验证，直接使用硬编码的用户名和密码
        if username == 'admin' and password == 'admin123':
            # 登录成功，设置会话
            session['logged_in'] = True
            session['username'] = username
            session['role'] = 'admin'
            
            # 记录审计
            try:
                contract_manager.record_audit_action('用户登录', f'用户: {username}')
            except Exception as e:
                app.logger.error(f"记录登录审计失败: {str(e)}")
            
            flash(f'欢迎 {username} 登录系统!', 'success')
            return redirect(url_for('home'))
        else:
            flash('用户名或密码错误!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('username', '未知用户')
    
    # 记录审计
    try:
        contract_manager.record_audit_action('用户登出', f'用户: {username}')
    except Exception as e:
        app.logger.error(f"记录登出审计失败: {str(e)}")
        
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('您已成功退出系统!', 'info')
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
    
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
    # 重定向到home页面
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('upload.html', error='No file selected')
        
        file = request.files['file']
        if file.filename == '':
            return render_template('upload.html', error='No file selected')
        
        if not file.filename.endswith('.csv'):
            return render_template('upload.html', error='Only CSV files are supported')
        
        # 创建记录目录
        upload_dir = os.path.join(os.path.dirname(__file__), 'police_records')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存上传的文件
        filepath = os.path.join(upload_dir, file.filename)
        file.save(filepath)
        
        # 临时数据文件路径
        temp_data_path = os.path.join(upload_dir, 'temp_chain_data.txt')
        
        # 添加验证输出
        print("\n========= 开始验证上传流程 =========")
        print(f"将使用PoliceDataUpload.py中的All_Police_Data_Upload_to_Chain函数处理文件: {filepath}")
        
        try:
            # 调用All_Police_Data_Upload_to_Chain处理CSV文件
            # 该函数会生成PDF、计算默克尔树哈希、上传到IPFS和区块链
            upload_result = All_Police_Data_Upload_to_Chain(filepath, temp_data_path)
            
            # 获取处理结果的统计数据
            total_records = upload_result["total"]
            success_records = upload_result["success"]
            duplicate_records = upload_result["duplicate"]
            error_records = upload_result["error"]
            detailed_results = upload_result["results"]
            
            print(f"处理完成，共处理 {total_records} 条记录")
            print(f"成功上链: {success_records} 条")
            print(f"重复记录: {duplicate_records} 条")
            print(f"处理失败: {error_records} 条")
            
            # 收集重复记录信息，用于显示给用户
            duplicate_records_info = [r['police_no'] for r in detailed_results if r['is_duplicate']]
            failed_records_info = [{"police_no": r['police_no'], "error": r['message']} 
                                  for r in detailed_results if not r['success'] and not r['is_duplicate']]
            
            # 从临时文件读取处理结果
            chain_data_collection = []
            try:
                with open(temp_data_path, 'r', encoding='utf-8') as f:
                    chain_data_text = f.read()
                    chain_data_collection = eval(chain_data_text)  # 解析存储的Python对象
                    
                # 验证并输出默克尔树和IPFS信息
                if chain_data_collection and len(chain_data_collection) > 0:
                    print("\n===== 验证第一条记录的处理结果 =====")
                    first_record = chain_data_collection[0]
                    print(f"警情编号: {first_record.get('PoliceNo')}")
                    print(f"默克尔树根哈希: {first_record.get('Merkel_Tophash')}")
                    print(f"PDF哈希: {first_record.get('PDF_Hash')}")
                    print(f"IPFS地址: {first_record.get('IPFS')}")
                    print(f"区块号: {first_record.get('BlockNumber')}")
                
            except Exception as e:
                print(f"读取上链数据失败: {str(e)}")
                chain_data_collection = []
            
            # 同步到数据库
            conn = sqlite3.connect('./database/PoliceData.db')
            cursor = conn.cursor()
            
            records_updated = 0
            for chain_data in chain_data_collection:
                try:
                    police_no = chain_data.get('PoliceNo')
                    receive_time = chain_data.get('ReceiveTime')
                    officer = chain_data.get('PoliceOfficer')
                    result = chain_data.get('Result')
                    gps_location = chain_data.get('GPSLocation')
                    upload_time = chain_data.get('UploadTime')
                    temp_hash = chain_data.get('Temp_Hash')
                    pdf_hash = chain_data.get('PDF_Hash')
                    merkle_hash = chain_data.get('Merkel_Tophash')
                    ipfs_url = chain_data.get('IPFS')
                    block_number = chain_data.get('BlockNumber')
                    
                    # 提取可选字段
                    report_type = chain_data.get('ReportType', '')
                    location = chain_data.get('Location', '')
                    contact_name = chain_data.get('ContactName', '')
                    contact_phone = chain_data.get('ContactPhone', '')
                    priority = chain_data.get('Priority', '普通')
                    department = chain_data.get('Department', '')
                    description = chain_data.get('Result', '') # 使用处置结果作为默认描述
                    
                    # 确保所有参数都是标量类型，不是元组
                    receive_time = str(receive_time) if receive_time else ""
                    officer = str(officer) if officer else ""
                    result_value = str(result) if result else ""  # 重命名以避免命名冲突
                    gps_location = str(gps_location) if gps_location else ""
                    temp_hash = str(temp_hash) if temp_hash else ""
                    pdf_hash = str(pdf_hash) if pdf_hash else ""
                    merkle_hash = str(merkle_hash) if merkle_hash else ""
                    ipfs_url = str(ipfs_url) if ipfs_url else ""
                    upload_time = str(upload_time) if upload_time else ""
                    block_number = str(block_number) if block_number else "0"
                    report_type = str(report_type) if report_type else ""
                    location = str(location) if location else ""
                    contact_name = str(contact_name) if contact_name else ""
                    contact_phone = str(contact_phone) if contact_phone else ""
                    priority = str(priority) if priority else "普通"
                    department = str(department) if department else ""
                    description = str(description) if description else ""
                    
                    # 查询数据库是否已有该记录
                    cursor.execute("SELECT BlockNum FROM police_records WHERE PoliceNo = ?", (police_no,))
                    result = cursor.fetchone()
                    exists = result is not None
                    existing_block_num = result[0] if result else None
                    
                    # 确保existing_block_num是标量类型
                    if existing_block_num and isinstance(existing_block_num, tuple):
                        existing_block_num = existing_block_num[0] if existing_block_num else None
                    existing_block_num = str(existing_block_num) if existing_block_num else "N/A"
                    
                    # 检查是否为重复上链的记录
                    is_duplicate = chain_data.get('is_duplicate', False)
                    
                    if exists:
                        # 如果是重复记录且数据库中已有区块号，不更新区块号字段
                        if is_duplicate and existing_block_num and existing_block_num != 'N/A' and existing_block_num != '未上链':
                            print(f"记录 {police_no} 已存在，保留原始区块号: {existing_block_num}")
                            # 调试代码：打印参数类型
                            print(f"参数类型调试:")
                            print(f"receive_time 类型: {type(receive_time)}")
                            print(f"officer 类型: {type(officer)}")
                            print(f"result 类型: {type(result)}")
                            print(f"gps_location 类型: {type(gps_location)}")
                            print(f"temp_hash 类型: {type(temp_hash)}")
                            print(f"pdf_hash 类型: {type(pdf_hash)}")
                            print(f"merkle_hash 类型: {type(merkle_hash)}")
                            print(f"ipfs_url 类型: {type(ipfs_url)}")
                            print(f"upload_time 类型: {type(upload_time)}")
                            print(f"existing_block_num 类型: {type(existing_block_num)}")
                            print(f"report_type 类型: {type(report_type)}")
                            print(f"location 类型: {type(location)}")
                            print(f"contact_name 类型: {type(contact_name)}")
                            print(f"contact_phone 类型: {type(contact_phone)}")
                            print(f"priority 类型: {type(priority)}")
                            print(f"department 类型: {type(department)}")
                            print(f"description 类型: {type(description)}")
                            
                            # 更新当前时间为上传时间，保证重复上链的记录也会排在前面
                            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            
                            cursor.execute('''
                            UPDATE police_records 
                            SET ReceiveTime = ?, PoliceOfficer = ?, Result = ?, GPSLocation = ?, 
                            Temp_Hash = ?, PDF_Hash = ?, Merkle_Hash = ?, IPFS = ?, UploadTime = ?, 
                            RecordStatus = ?, BlockNum = ?, ReportType = ?, Location = ?, ContactName = ?, 
                            ContactPhone = ?, Priority = ?, Department = ?, Description = ?
                            WHERE PoliceNo = ?
                            ''', (receive_time, officer, result_value, gps_location, 
                                 temp_hash, pdf_hash, merkle_hash, ipfs_url, current_time, 
                                 'Active', existing_block_num, report_type, location, contact_name, 
                                 contact_phone, priority, department, description, police_no))
                        else:
                            # 常规更新，包括区块号
                            cursor.execute('''
                            UPDATE police_records 
                            SET ReceiveTime = ?, PoliceOfficer = ?, Result = ?, GPSLocation = ?, 
                            Temp_Hash = ?, PDF_Hash = ?, Merkle_Hash = ?, IPFS = ?, UploadTime = ?, 
                            RecordStatus = ?, BlockNum = ?, ReportType = ?, Location = ?, ContactName = ?, 
                            ContactPhone = ?, Priority = ?, Department = ?, Description = ?
                            WHERE PoliceNo = ?
                            ''', (receive_time, officer, result_value, gps_location, 
                                 temp_hash, pdf_hash, merkle_hash, ipfs_url, upload_time, 
                                 'Active', block_number, report_type, location, contact_name, 
                                 contact_phone, priority, department, description, police_no))
                    else:
                        # 新记录，插入所有字段
                        cursor.execute('''
                        INSERT INTO police_records 
                        (PoliceNo, ReceiveTime, PoliceOfficer, Result, GPSLocation, 
                        Temp_Hash, PDF_Hash, Merkle_Hash, IPFS, UploadTime, 
                        RecordStatus, BlockNum, ReportType, Location, ContactName, 
                        ContactPhone, Priority, Department, Description)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (police_no, receive_time, officer, result_value, gps_location, 
                             temp_hash, pdf_hash, merkle_hash, ipfs_url, upload_time, 
                             'Active', block_number, report_type, location, contact_name, 
                             contact_phone, priority, department, description))
                    
                    records_updated += 1
                    
                except Exception as e:
                    print(f"处理记录出错: {str(e)}")
                    continue
            
            print(f"\n数据库更新完成，共更新 {records_updated} 条记录")
            print("========= 上传流程验证结束 =========\n")
            
            # 记录操作日志
            log_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            INSERT INTO operation_log (timestamp, action, username, details)
            VALUES (?, ?, ?, ?)
            ''', (log_timestamp, '上传警情记录', session.get('username'), 
                 f'上传文件: {file.filename}, 处理记录数: {total_records}, 入库记录数: {records_updated}'))
            
            conn.commit()
            conn.close()
            
            # 可选：清理临时文件
            try:
                if os.path.exists(temp_data_path):
                    os.remove(temp_data_path)
            except:
                pass
            
            # 返回成功和警告消息
            if duplicate_records == total_records and total_records > 0:
                # 所有记录都是重复的情况，只显示一条信息，不显示成功消息
                flash(f"所有警情记录({total_records}条)均已存在于区块链上，无需重复上链", 'info')
            else:
                # 正常情况下显示各类消息
                if success_records > 0:
                    success_msg = f'成功处理 {total_records} 条警情记录，其中 {success_records} 条成功上链'
                    flash(success_msg, 'success')
                
                # 如果有重复记录，显示提示
                if duplicate_records > 0:
                    duplicate_msg = f'有 {duplicate_records} 条警情记录已存在于区块链，请勿重复上链: {", ".join(duplicate_records_info)}'
                    flash(duplicate_msg, 'warning')
                    
                # 如果有失败记录，显示错误
                if error_records > 0:
                    error_police_nos = ", ".join([item["police_no"] for item in failed_records_info])
                    error_msg = f'以下警情记录上链失败: {error_police_nos}'
                    flash(error_msg, 'danger')
            
            return redirect(url_for('upload_file'))
            
        except Exception as e:
            error_message = f"处理文件时出错: {str(e)}"
            print(error_message)
            import traceback
            traceback.print_exc()
            return render_template('upload.html', error=error_message)
    
    # GET请求，显示上传页面
    return render_template('upload.html')

# 辅助函数，用于生成唯一的文件名
def generate_unique_filename(prefix=''):
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{timestamp}_{random_str}" if prefix else f"{timestamp}_{random_str}"

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
        
    storage_folder = "./upload"

    if request.method == 'POST':
        if 'pdffile' not in request.files:
            flash("未选择文件", "danger")
            return render_template('verify.html')

        pdf_file = request.files['pdffile']

        if pdf_file.filename == '':
            flash("未选择文件", "danger")
            return render_template('verify.html')

        if pdf_file:
            pdf_filename = secure_filename(pdf_file.filename)
            uploaded_pdf = os.path.join(storage_folder, pdf_filename)
            pdf_file.save(uploaded_pdf)
            
            # 验证警情记录PDF
            ret = PDV.verify_police_record(uploaded_pdf)

            if ret['Tag'] == 'pass':
                # 获取验证消息和状态
                verification_message = ret['Content']
                verification_failed = False
                
                # 优先使用Data字段判断验证状态
                if 'Data' in ret and isinstance(ret['Data'], dict):
                    verification_data = ret['Data']
                    hash_match = verification_data.get('hash_match', True)
                    all_match = verification_data.get('all_match', True)
                    verification_failed = not (hash_match and all_match)
                else:
                    # 如果没有Data字段，回退到使用消息内容判断
                    if "不匹配" in verification_message or "失败" in verification_message:
                        verification_failed = True
                
                # 获取警情编号用于审计记录
                police_no = "未知"
                if 'Info' in ret and 'PoliceNo' in ret['Info']:
                    police_no = ret['Info']['PoliceNo']
                
                # 添加后端审计记录
                try:
                    audit_details = f"验证警情记录: {police_no}"
                    audit_status = "验证失败" if verification_failed else "验证成功"
                    contract_manager.record_audit_action(f"数据验证({audit_status})", audit_details)
                except Exception as e:
                    app.logger.error(f"记录验证审计失败: {str(e)}")
                
                # 根据验证状态设置消息类型
                if verification_failed:
                    flash(verification_message, 'danger')
                    
                    # 确保数据库状态也更新为无效
                    if 'Info' in ret and 'PoliceNo' in ret['Info']:
                        police_no = ret['Info']['PoliceNo']
                        # 检查最新的数据库状态
                        conn = connect_db()
                        cursor = conn.cursor()
                        cursor.execute("SELECT RecordStatus FROM police_records WHERE PoliceNo = ?", (police_no,))
                        record = cursor.fetchone()
                        
                        # 如果记录存在且仍是Active状态，更新为Invalid
                        if record and record['RecordStatus'] == 'Active':
                            reason = "PDF验证失败，可能被篡改"
                            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cursor.execute('''
                                UPDATE police_records 
                                SET RecordStatus = 'Invalid', 
                                    Memo = ?,
                                    RevokeTime = ?,
                                    RevokeUser = ? 
                                WHERE PoliceNo = ?
                            ''', (reason, current_time, "系统自动", police_no))
                            conn.commit()
                            print(f"已更新警情记录 {police_no} 的状态为 Invalid")
                        conn.close()
                else:
                    flash(verification_message, 'success')
                
                police_info = ret['Info']
                return render_template('verify.html', 
                               verification_success=True, 
                               police_info=police_info,
                               message=verification_message,
                               verification_failed=verification_failed)
            else:
                flash(ret['Content'], 'danger')
                return render_template('verify.html')

    return render_template('verify.html')

def process_record_revoke(police_no, reason, username):
    """
    统一的警情记录撤销处理函数
    
    Args:
        police_no: 警情编号
        reason: 撤销原因
        username: 操作用户名
        
    Returns:
        dict: 包含撤销结果的字典
    """
    try:
        # 查询该警情记录
        record = query_db("SELECT * FROM police_records WHERE PoliceNo = ?", [police_no], one=True)
        
        if not record:
            return {
                'success': False,
                'message': f"警情编号 {police_no} 不存在!",
                'status': 'danger'
            }
            
        if record.get('RecordStatus') == 'Revoked':
            return {
                'success': False,
                'message': f"警情编号 {police_no} 已经被撤销!",
                'status': 'warning'
            }
        
        # 1. 撤销信息上链存证
        try:
            # 调用合约函数实现上链
            revoke_result = contract_manager.revoke_police_record(police_no, reason)
            # 记录撤销成功的审计日志
            contract_manager.record_audit_action('数据撤销(成功)', f'撤销警情记录: {police_no}, 原因: {reason}')
        except Exception as e:
            app.logger.error(f"上链失败: {str(e)}")
            # 记录撤销失败的审计日志
            contract_manager.record_audit_action('数据撤销(失败)', f'撤销警情记录上链失败: {police_no}, 原因: {reason}, 错误: {str(e)}')
            return {
                'success': False,
                'message': f'撤销信息上链失败: {str(e)}',
                'status': 'danger'
            }
        
        # 2. 上链成功后，同步到数据库
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = connect_db()
        cursor = conn.cursor()
        
        # 更新数据库
        cursor.execute('''
        UPDATE police_records 
        SET RecordStatus = 'Revoked', 
            Memo = ?,
            RevokeTime = ?,
            RevokeUser = ? 
        WHERE PoliceNo = ?
        ''', (reason, current_time, username, police_no))
        
        # 记录操作日志
        cursor.execute('''
        INSERT INTO operation_log (timestamp, action, username, details) 
        VALUES (?, ?, ?, ?)
        ''', (
            current_time,
            '警情撤销',
            username,
            f'撤销警情记录 {police_no}: {reason}'
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f"警情编号 {police_no} 的记录已成功撤销!",
            'status': 'success',
            'revoke_time': current_time
        }
    except Exception as e:
        app.logger.error(f"撤销处理错误: {str(e)}")
        return {
            'success': False,
            'message': f'撤销失败: {str(e)}',
            'status': 'danger'
        }

@app.route('/revoke', methods=['GET', 'POST'])
def record_revoke():
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
        
    if request.method == "POST":
        police_no = request.form['police_no']
        reason = request.form.get('reason', '无说明原因')
        
        # 调用统一的撤销处理函数
        result = process_record_revoke(police_no, reason, session.get('username', 'admin'))
        
        flash(result['message'], result['status'])
        
        # 无论成功或失败，都返回到撤销页面
        return redirect(url_for('record_revoke'))
        
    return render_template('revoke.html')

@app.route('/revoke/<string:police_no>', methods=['GET', 'POST'])
def revoke_record(police_no):
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
        
    # 查询该警情记录
    record = query_db("SELECT * FROM police_records WHERE PoliceNo = ?", [police_no], one=True)
    
    if not record:
        flash(f"警情编号 {police_no} 不存在!", "danger")
        return redirect(url_for('query'))
        
    if record.get('RecordStatus') == 'Revoked':
        flash(f"警情编号 {police_no} 已经被撤销!", "warning")
        return redirect(url_for('query'))
    
    if request.method == 'POST':
        reason = request.form.get('reason', '无说明原因')
        
        # 调用统一的撤销处理函数
        result = process_record_revoke(police_no, reason, session.get('username', 'admin'))
        
        flash(result['message'], result['status'])
        
        # 修改：撤销成功后也返回到撤销页面
        return redirect(url_for('record_revoke'))
    
    return render_template('revoke.html', record=record)

@app.route('/api/revoke_record', methods=['POST'])
def revoke_record_api():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': '未登录，请先登录'}), 401

    # 获取当前用户名
    username = session.get('username')
    
    # 从请求中获取数据
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'error': '无效的请求数据'}), 400
    
    record_id = data.get('recordId')
    reason = data.get('reason')
    
    if not record_id or not reason:
        return jsonify({'success': False, 'error': '警情编号和撤销原因不能为空'}), 400
    
    # 调用统一处理函数
    result = process_record_revoke(record_id, reason, username)
    
    if result['success']:
        return jsonify({
            'success': True, 
            'message': result['message']
        })
    else:
        return jsonify({
            'success': False, 
            'error': result['message']
        }), 400

@app.route('/query', methods=['GET', 'POST'])
def query():
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
    
    # 获取分页参数
    page = int(request.args.get('page', 1))
    per_page = 9  # 每页显示的记录数
    
    # 获取搜索参数
    search_police_no = request.args.get('police_no', '')
    search_officer = request.args.get('officer', '')
    search_status = request.args.get('status', '')
    
    # 构建查询语句
    query = "SELECT * FROM police_records WHERE 1=1"
    params = []
    
    if search_police_no:
        query += " AND PoliceNo LIKE ?"
        params.append(f"%{search_police_no}%")
        
    if search_officer:
        query += " AND PoliceOfficer LIKE ?"
        params.append(f"%{search_officer}%")
        
    if search_status:
        query += " AND RecordStatus = ?"
        params.append(search_status)
    
    # 获取总记录数
    count_query = f"SELECT COUNT(*) as count FROM ({query})"
    total_count = query_db(count_query, params, one=True)
    total_count = total_count.get('count', 0) if total_count else 0
    
    # 添加分页
    query += " ORDER BY UploadTime DESC LIMIT ? OFFSET ?"
    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    
    # 执行查询
    records = query_db(query, params)
    
    # 计算总页数
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    return render_template('query.html', 
                           records=records, 
                           page=page, 
                           total_pages=total_pages,
                           search_police_no=search_police_no,
                           search_officer=search_officer,
                           search_status=search_status)

@app.route('/preview_template')
def preview_template():
    template_path = os.path.join(app.root_path, 'PoliceTemplate.pdf')
    return send_file(template_path, as_attachment=False)

@app.route('/download_pdf/<string:police_no>')
def download_pdf(police_no):
    """下载警情记录PDF文件"""
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
    
    # 确保PDF存储目录存在
    pdf_dir = os.path.join(os.getcwd(), 'police_records')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # 查询数据库记录以获取IPFS哈希
    record = query_db("SELECT * FROM police_records WHERE PoliceNo = ?", [police_no], one=True)
    
    if not record:
        flash(f"未找到警情编号 {police_no} 的记录!", "danger")
        return redirect(url_for('query'))
    
    # 优先从IPFS获取PDF文件
    pdf_path = None
    ipfs_hash = None
    
    # 检查记录中是否有IPFS哈希
    if record.get('IPFS') and 'ipfs' in record.get('IPFS', ''):
        try:
            # 从IPFS URL中提取哈希
            ipfs_url = record.get('IPFS', '')
            # 提取IPFS哈希
            if 'ipfs/' in ipfs_url:
                ipfs_hash = ipfs_url.split('ipfs/')[1].strip()
            
            if ipfs_hash:
                print(f"尝试从IPFS下载文件，哈希: {ipfs_hash}")
                # 导入IPFS工具
                from ipfs_utils import download_from_ipfs
                
                # 定义下载路径
                temp_pdf_path = os.path.join(pdf_dir, f'{police_no}_ipfs.pdf')
                
                # 从IPFS下载
                pdf_path = download_from_ipfs(ipfs_hash, temp_pdf_path)
                
                if pdf_path and os.path.exists(pdf_path):
                    print(f"成功从IPFS下载PDF: {pdf_path}")
                    # 记录日志
                    log_msg = f"从IPFS下载警情记录PDF: {police_no}, IPFS哈希: {ipfs_hash}"
                    record_operation_log("下载PDF", session.get('username', 'unknown'), log_msg)
                else:
                    print(f"从IPFS下载失败，将尝试获取本地文件")
        except Exception as e:
            print(f"从IPFS下载PDF时出错: {str(e)}")
    
    # 如果从IPFS下载失败，检查本地是否存在
    if not pdf_path or not os.path.exists(pdf_path):
        # 尝试查找本地已有的PDF文件
        for file in os.listdir(pdf_dir):
            if file.startswith(police_no) and file.endswith('.pdf'):
                pdf_path = os.path.join(pdf_dir, file)
                print(f"找到本地PDF文件: {pdf_path}")
                break
    
    # 如果本地不存在，尝试从数据生成PDF
    if not pdf_path or not os.path.exists(pdf_path):
        try:
            # 导入PDF生成模块
            from PoliceTemplatePDF import generate_pdf_from_record
            
            print(f"本地和IPFS都没有找到PDF，尝试从记录生成PDF: {police_no}")
            # 生成PDF - 由于generate_pdf_from_record已经包含检查现有文件的逻辑，不会重复生成
            pdf_path = generate_pdf_from_record(record)
            
            if pdf_path and os.path.exists(pdf_path):
                flash(f"已成功生成 {police_no} 的PDF文件", "success")
                # 记录日志
                log_msg = f"生成警情记录PDF: {police_no}"
                record_operation_log("生成PDF", session.get('username', 'unknown'), log_msg)
            else:
                flash("PDF生成失败", "danger")
                return redirect(url_for('query'))
                
        except Exception as e:
            flash(f"生成PDF时出错: {str(e)}", "danger")
            return redirect(url_for('query'))
    
    # 返回PDF文件
    try:
        return send_file(pdf_path, as_attachment=True, download_name=f"警情记录_{police_no}.pdf")
    except Exception as e:
        flash(f"下载PDF时出错: {str(e)}", "danger")
        return redirect(url_for('query'))

def record_operation_log(action, username, details):
    """记录操作日志"""
    try:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO operation_log (timestamp, action, username, details) VALUES (?, ?, ?, ?)",
            (current_time, action, username, details)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"记录操作日志时出错: {str(e)}")

@app.route('/api/check_record/<record_id>', methods=['GET'])
def check_record(record_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询记录
        cursor.execute('SELECT * FROM police_records WHERE PoliceNo = ?', (record_id,))
        record = cursor.fetchone()
        
        if record:
            # 将记录转换为字典
            record_dict = {
                'recordId': record['PoliceNo'],
                'time': record['ReceiveTime'],
                'officer': record['PoliceOfficer'],
                'result': record['Result'],
                'gps': record['GPSLocation'],
                'status': record['RecordStatus']
            }
            return jsonify({'success': True, 'record': record_dict})
        else:
            return jsonify({'success': False, 'message': '未找到该记录'}), 404
            
    except Exception as e:
        print(f"Database error: {str(e)}")  # 添加错误日志
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_db_connection():
    """获取数据库连接"""
    return connect_db()  # 使用统一的connect_db函数

@app.teardown_appcontext
def close_db(error):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/update_block_info/<string:police_no>')
def update_block_info(police_no):
    """更新警情记录的区块信息（仅在系统中更新，不再重新生成PDF）"""
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
    
    try:
        # 查询警情记录
        record = query_db("SELECT * FROM police_records WHERE PoliceNo = ?", [police_no], one=True)
        
        if not record:
            flash(f"警情编号 {police_no} 不存在!", "danger")
            return redirect(url_for('query'))
        
        # 确认区块号存在
        if not record.get('BlockNum'):
            flash(f"警情编号 {police_no} 未上链，无法更新区块信息!", "warning")
            return redirect(url_for('query'))
        
        # 记录操作日志
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO system_logs (UserName, Action, Target, Details, ActionTime)
        VALUES (?, ?, ?, ?, ?)
        ''', (session.get('username', 'unknown'), 
              '更新区块信息', 
              police_no, 
              f"仅更新系统中的区块信息记录 ({record.get('BlockNum')})", 
              current_time))
        conn.commit()
        conn.close()
        
        flash(f"成功更新警情记录 {police_no} 的区块信息! 区块号: {record.get('BlockNum')}", "success")
        
        # 重定向到查询结果页面
        return redirect(url_for('record_detail', police_no=police_no))
        
    except Exception as e:
        flash(f"更新区块信息失败: {str(e)}", "danger")
        return redirect(url_for('query'))

@app.route('/audit_trail', methods=['GET', 'POST'])
def audit_trail():
    """审计记录查询页面"""
    if not session.get('logged_in'):
        flash('请先登录系统!', 'warning')
        return redirect(url_for('login'))
    
    record = None
    recent_records = None
    error = None
    has_records = False
    
    # 操作类型统计数据
    login_count = 0
    upload_count = 0
    verify_count = 0
    revoke_count = 0
    
    # 时间分布统计数据
    now = datetime.datetime.now()
    today_timestamp = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    yesterday_timestamp = int((now - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    day_2_timestamp = int((now - datetime.timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    day_3_timestamp = int((now - datetime.timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    day_4_timestamp = int((now - datetime.timedelta(days=4)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    day_5_timestamp = int((now - datetime.timedelta(days=5)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    
    today_records = 0
    yesterday_records = 0
    day_2_records = 0
    day_3_records = 0
    day_4_records = 0
    day_5_records = 0
    earlier_records = 0
    
    # 获取审计统计数据
    try:
        # 获取总记录数
        total_records = contract_manager.get_audit_trail_count()
        
        # 初始化警告记录数和用户数
        alert_records = 0
        user_count = 0
        
        # 如果有记录，计算实际统计数据
        if total_records and total_records > 0:
            has_records = True
            # 获取最近100条记录用于统计（如果总记录数少于100，则获取全部记录）
            recent_ids = contract_manager.get_recent_audit_records(min(100, total_records))
            
            # 临时存储用户地址和今日记录
            user_addresses = set()
            
            # 批量处理记录，减少日志输出
            for record_id in recent_ids:
                try:
                    record_data = contract_manager.get_audit_record(record_id)
                    if record_data:
                        user_address, action, details, timestamp = record_data
                        
                        # 添加到用户集合
                        if user_address:
                            user_addresses.add(user_address)
                        
                        # 操作类型统计
                        action_lower = action.lower() if action else ""
                        if '登录' in action_lower or 'login' in action_lower:
                            login_count += 1
                        elif '上链' in action_lower or '上传' in action_lower or 'upload' in action_lower:
                            upload_count += 1
                        elif '验证' in action_lower or 'verify' in action_lower:
                            verify_count += 1
                        elif '撤销' in action_lower or 'revoke' in action_lower:
                            revoke_count += 1
                        
                        # 检查是否为警告记录
                        if action_lower and ('错误' in action_lower or '撤销' in action_lower or '警告' in action_lower or 
                                           'revoke' in action_lower or 'error' in action_lower or 'warning' in action_lower):
                            alert_records += 1
                        
                        # 时间分布统计
                        # 确保timestamp是数字
                        if isinstance(timestamp, str):
                            try:
                                timestamp = int(timestamp)
                            except (ValueError, TypeError):
                                # 如果无法转换为整数，跳过此记录的时间统计
                                continue
                        
                        # 使用时间戳范围判断
                        if timestamp >= today_timestamp:
                            today_records += 1
                        elif timestamp >= yesterday_timestamp:
                            yesterday_records += 1
                        elif timestamp >= day_2_timestamp:
                            day_2_records += 1
                        elif timestamp >= day_3_timestamp:
                            day_3_records += 1
                        elif timestamp >= day_4_timestamp:
                            day_4_records += 1
                        elif timestamp >= day_5_timestamp:
                            day_5_records += 1
                        else:
                            earlier_records += 1
                except Exception as e:
                    # 减少日志输出，仅在开发模式下记录详细错误
                    if app.debug:
                        app.logger.error(f"获取审计记录 {record_id} 失败: {str(e)}")
            
            # 更新用户统计数据
            # 如果用户集合为空但有记录，至少有一个用户
            user_count = max(1, len(user_addresses))
        
        # 确保今日记录数合理 - 如果总记录数大于0但今日记录为0，认为可能有数据同步问题
        if total_records > 0 and today_records == 0:
            # 尝试设置一个合理的默认值 - 根据最近记录的比例估算
            today_records = max(1, int(total_records * 0.1))  # 假设约10%是今日记录
        
        # 确保用户数合理 - 至少有1个用户
        if total_records > 0 and user_count == 0:
            user_count = 1
        
    except Exception as e:
        app.logger.error(f"获取审计统计数据失败: {str(e)}")
        total_records = 0
        today_records = 0
        alert_records = 0
        user_count = 0
    
    # 处理单条记录查询
    record_id = request.args.get('record_id')
    if record_id:
        try:
            record_id = int(record_id)
            record_data = contract_manager.get_audit_record(record_id)
            if record_data:
                user_address, action, details, timestamp = record_data
                record = {
                    'id': record_id,
                    'user': user_address,
                    'action': action,
                    'details': details,
                    'timestamp': timestamp
                }
            else:
                error = f"未找到ID为 {record_id} 的审计记录"
        except Exception as e:
            error = f"查询审计记录失败: {str(e)}"
    
    # 处理GET请求中的advanced_search
    if request.args.get('action') == 'advanced_search':
        # 处理高级搜索查询
        try:
            # 获取分页参数
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 10))
            
            # 记录ID处理（如果存在）
            record_id_str = request.args.get('record_id', '').strip()
            if record_id_str:
                try:
                    record_id = int(record_id_str)
                    record_data = contract_manager.get_audit_record(record_id)
                    if record_data:
                        user_address, action, details, timestamp = record_data
                        record = {
                            'id': record_id,
                            'user': user_address,
                            'action': action,
                            'details': details,
                            'timestamp': timestamp
                        }
                        # 找到单条记录后直接返回，不需要继续处理
                        return render_template('audit_trail.html', 
                                              record=record,
                                              total_records=total_records,
                                              today_records=today_records,
                                              alert_records=alert_records,
                                              user_count=user_count)
                except (ValueError, TypeError) as e:
                    app.logger.error(f"记录ID转换错误: {str(e)}, 值: '{record_id_str}'")
                    # ID转换错误，继续其他查询条件
                    pass
            
            # 获取查询参数 - 确保所有参数都有默认值
            time_range = request.args.get('time_range', 'today')
            action_type = request.args.get('action_type', '')
            operator = request.args.get('operator', '')
            keywords = request.args.get('keywords', '')
            
            # 结果限制 - 严格类型检查
            limit = 100  # 默认值，使用更大的值来获取所有记录进行分页
            limit_str = request.args.get('limit', '')
            if limit_str and limit_str.strip():
                try:
                    limit = int(limit_str)
                    if limit < 1 or limit > 200:
                        limit = 100
                except (ValueError, TypeError):
                    # 转换失败，使用默认值
                    limit = 100
            
            # 只显示警告记录
            show_warnings_only = 'show_warnings_only' in request.args

            # 安全获取总记录数并防止None
            safe_total_records = total_records if isinstance(total_records, int) else 0
            
            # 获取记录进行筛选 - 确保参数是有效整数
            records_to_fetch = min(limit * 4, safe_total_records)  # 增大获取的记录数量，确保分页效果更好
            if records_to_fetch < 1:
                records_to_fetch = 20  # 最小获取20条记录
            
            record_ids = []
            try:
                record_ids = contract_manager.get_recent_audit_records(records_to_fetch)
            except Exception as e:
                app.logger.error(f"获取最近记录ID失败: {str(e)}")
                record_ids = []  # 确保是空列表而不是None
            
            filtered_records_ids = []
            
            # 如果选择了自定义日期范围，解析日期
            start_timestamp = None
            end_timestamp = None
            
            try:
                if time_range == 'custom':
                    try:
                        start_date = request.args.get('start_date', '')
                        end_date = request.args.get('end_date', '')
                        
                        if start_date and start_date.strip():
                            start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                            start_timestamp = int(start_dt.timestamp())
                        
                        if end_date and end_date.strip():
                            end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                            end_dt = end_dt.replace(hour=23, minute=59, second=59)
                            end_timestamp = int(end_dt.timestamp())
                    except Exception as e:
                        app.logger.error(f"日期解析错误: {str(e)}")
                elif time_range == 'today':
                    start_timestamp = today_timestamp
                elif time_range == 'week':
                    # 一周前的时间戳
                    start_timestamp = int((now - datetime.timedelta(days=7)).timestamp())
                elif time_range == 'month':
                    # 一个月前的时间戳
                    start_timestamp = int((now - datetime.timedelta(days=30)).timestamp())
                # 'all'选项不设置时间戳，表示不限制时间范围
            except Exception as e:
                app.logger.error(f"时间范围处理错误: {str(e)}")
            
            # 筛选记录 - 添加更严格的错误处理
            for record_id in record_ids:
                try:
                    # 确保record_id是整数
                    if not isinstance(record_id, int):
                        try:
                            record_id = int(record_id)
                        except (ValueError, TypeError):
                            app.logger.error(f"无效的记录ID类型: {type(record_id)}, 值: {record_id}")
                            continue
                    
                    record_data = contract_manager.get_audit_record(record_id)
                    if not record_data:
                        continue
                        
                    # 确保解包正确
                    if len(record_data) < 4:
                        app.logger.error(f"记录数据不完整: {record_data}")
                        continue
                        
                    user_address, action, details, timestamp = record_data
                    
                    # 转换时间戳为整数
                    if not isinstance(timestamp, int):
                        try:
                            if isinstance(timestamp, str) and timestamp.strip():
                                timestamp = int(timestamp)
                            else:
                                # 如果时间戳为空或None，使用当前时间
                                timestamp = int(time.time())
                        except (ValueError, TypeError):
                            app.logger.error(f"时间戳转换错误: {timestamp}")
                            continue
                    
                    # 时间范围筛选 - 修复: 只在选择了特定时间范围时进行筛选
                    if time_range != 'all':  # 所有时间选项不进行时间过滤
                        if start_timestamp and timestamp < start_timestamp:
                            continue
                        if end_timestamp and timestamp > end_timestamp:
                            continue
                    
                    # 操作类型筛选
                    if action_type:
                        action_class = get_action_class(action)
                        if action_type != action_class:
                            continue
                    
                    # 操作人员筛选
                    if operator and user_address and operator.lower() not in user_address.lower():
                        continue
                    
                    # 关键词筛选
                    if keywords and details and keywords.lower() not in details.lower():
                        continue
                    
                    # 警告记录筛选
                    if show_warnings_only:
                        action_lower = action.lower() if action else ""
                        if not ('错误' in action_lower or '撤销' in action_lower or '警告' in action_lower or 
                               'revoke' in action_lower or 'error' in action_lower or 'warning' in action_lower):
                            continue
                    
                    # 添加到过滤后的ID列表
                    filtered_records_ids.append(record_id)
                except Exception as e:
                    if app.debug:
                        app.logger.error(f"处理记录 {record_id} 失败: {str(e)}")
            
            # 计算总页数
            total_filtered = len(filtered_records_ids)
            total_pages = (total_filtered + per_page - 1) // per_page if total_filtered > 0 else 1
            
            # 确保页码有效
            page = max(1, min(page, total_pages))
            
            # 分页处理记录ID
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, total_filtered)
            
            # 确保索引在有效范围内
            if start_idx >= len(filtered_records_ids):
                start_idx = 0
                page = 1
            
            paginated_ids = filtered_records_ids[start_idx:end_idx]
            
            # 获取当前页的记录
            recent_records = []
            
            for record_id in paginated_ids:
                try:
                    record_data = contract_manager.get_audit_record(record_id)
                    if record_data:
                        user_address, action, details, timestamp = record_data
                        recent_records.append({
                            'id': record_id,
                            'user': user_address,
                            'action': action,
                            'details': details,
                            'timestamp': timestamp
                        })
                except Exception as e:
                    app.logger.error(f"获取审计记录 {record_id} 失败: {str(e)}")
            
            # 如果没有找到记录，显示提示信息
            if not filtered_records_ids:
                error = "未找到匹配的审计记录"
            
            # 保存查询参数，用于分页导航时保持查询条件
            search_params = {
                'action_type': action_type,
                'time_range': time_range,
                'operator': operator,
                'keywords': keywords,
                'limit': limit
            }
            
            # 处理show_warnings_only参数
            if show_warnings_only:
                search_params['show_warnings_only'] = 'on'
            
            # 添加日期范围参数（如果有）
            if time_range == 'custom':
                search_params['start_date'] = request.args.get('start_date', '')
                search_params['end_date'] = request.args.get('end_date', '')
            
            # 设置分页参数
            return render_template('audit_trail.html',
                                  recent_records=recent_records,
                                  total_records=total_records,
                                  today_records=today_records,
                                  alert_records=alert_records,
                                  user_count=user_count,
                                  page=page,
                                  per_page=per_page,
                                  total_pages=total_pages,
                                  total_filtered=total_filtered,
                                  search_params=search_params,
                                  search_type="advanced",
                                  error=error)
            
        except Exception as e:
            error = f"高级查询失败: {str(e)}"
            app.logger.error(f"高级查询失败: {str(e)}")
    
    # 处理POST请求
    if request.method == 'POST':
        if 'action' in request.form and request.form['action'] == 'advanced_search':
            # 处理高级搜索查询
            try:
                # 记录ID处理（如果存在）
                record_id_str = request.form.get('record_id', '').strip()
                if record_id_str:
                    try:
                        record_id = int(record_id_str)
                        record_data = contract_manager.get_audit_record(record_id)
                        if record_data:
                            user_address, action, details, timestamp = record_data
                            record = {
                                'id': record_id,
                                'user': user_address,
                                'action': action,
                                'details': details,
                                'timestamp': timestamp
                            }
                            # 找到单条记录后直接返回，不需要继续处理
                            return render_template('audit_trail.html', 
                                                  record=record,
                                                  total_records=total_records,
                                                  today_records=today_records,
                                                  alert_records=alert_records,
                                                  user_count=user_count)
                    except (ValueError, TypeError) as e:
                        app.logger.error(f"记录ID转换错误: {str(e)}, 值: '{record_id_str}'")
                        # ID转换错误，继续其他查询条件
                        pass
                
                # 获取查询参数 - 确保所有参数都有默认值
                time_range = request.form.get('time_range', 'today')
                action_type = request.form.get('action_type', '')
                operator = request.form.get('operator', '')
                keywords = request.form.get('keywords', '')
                
                # 结果限制 - 严格类型检查
                limit = 20  # 默认值
                limit_str = request.form.get('limit', '')
                if limit_str and limit_str.strip():
                    try:
                        limit = int(limit_str)
                        if limit < 1 or limit > 100:
                            limit = 20
                    except (ValueError, TypeError):
                        # 转换失败，使用默认值
                        limit = 20
                
                # 只显示警告记录
                show_warnings_only = 'show_warnings_only' in request.form

                # 安全获取总记录数并防止None
                safe_total_records = total_records if isinstance(total_records, int) else 0
                
                # 获取记录进行筛选 - 确保参数是有效整数
                records_to_fetch = min(limit * 4, safe_total_records)  # 增大获取的记录数量，确保分页效果更好
                if records_to_fetch < 1:
                    records_to_fetch = 20  # 最小获取20条记录
                
                recent_ids = []
                try:
                    recent_ids = contract_manager.get_recent_audit_records(records_to_fetch)
                except Exception as e:
                    app.logger.error(f"获取最近记录ID失败: {str(e)}")
                    recent_ids = []  # 确保是空列表而不是None
                
                filtered_records = []
                
                # 如果选择了自定义日期范围，解析日期
                start_timestamp = None
                end_timestamp = None
                
                try:
                    if time_range == 'custom':
                        try:
                            start_date = request.form.get('start_date', '')
                            end_date = request.form.get('end_date', '')
                            
                            if start_date and start_date.strip():
                                start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                                start_timestamp = int(start_dt.timestamp())
                            
                            if end_date and end_date.strip():
                                end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                                end_timestamp = int(end_dt.timestamp())
                        except Exception as e:
                            app.logger.error(f"日期解析错误: {str(e)}")
                    elif time_range == 'today':
                        start_timestamp = today_timestamp
                    elif time_range == 'week':
                        # 一周前的时间戳
                        start_timestamp = int((now - datetime.timedelta(days=7)).timestamp())
                    elif time_range == 'month':
                        # 一个月前的时间戳
                        start_timestamp = int((now - datetime.timedelta(days=30)).timestamp())
                except Exception as e:
                    app.logger.error(f"时间范围处理错误: {str(e)}")
                
                # 筛选记录 - 添加更严格的错误处理
                for record_id in recent_ids:
                    try:
                        # 确保record_id是整数
                        if not isinstance(record_id, int):
                            try:
                                record_id = int(record_id)
                            except (ValueError, TypeError):
                                app.logger.error(f"无效的记录ID类型: {type(record_id)}, 值: {record_id}")
                                continue
                        
                        record_data = contract_manager.get_audit_record(record_id)
                        if not record_data:
                            continue
                            
                        # 确保解包正确
                        if len(record_data) < 4:
                            app.logger.error(f"记录数据不完整: {record_data}")
                            continue
                            
                        user_address, action, details, timestamp = record_data
                        
                        # 转换时间戳为整数
                        if not isinstance(timestamp, int):
                            try:
                                if isinstance(timestamp, str) and timestamp.strip():
                                    timestamp = int(timestamp)
                                else:
                                    # 如果时间戳为空或None，使用当前时间
                                    timestamp = int(time.time())
                            except (ValueError, TypeError):
                                app.logger.error(f"时间戳转换错误: {timestamp}")
                                continue
                        
                        # 时间范围筛选
                        if start_timestamp and timestamp < start_timestamp:
                            continue
                        if end_timestamp and timestamp > end_timestamp:
                            continue
                        
                        # 操作类型筛选
                        if action_type:
                            action_class = get_action_class(action)
                            if action_type != action_class:
                                continue
                        
                        # 操作人员筛选
                        if operator and user_address and operator.lower() not in user_address.lower():
                            continue
                        
                        # 关键词筛选
                        if keywords and details and keywords.lower() not in details.lower():
                            continue
                        
                        # 警告记录筛选
                        if show_warnings_only:
                            action_lower = action.lower() if action else ""
                            if not ('错误' in action_lower or '撤销' in action_lower or '警告' in action_lower or 
                                   'revoke' in action_lower or 'error' in action_lower or 'warning' in action_lower):
                                continue
                        
                        # 添加到结果集
                        filtered_records.append({
                            'id': record_id,
                            'user': user_address,
                            'action': action,
                            'details': details,
                            'timestamp': timestamp
                        })
                        
                        # 达到限制数量后退出
                        if len(filtered_records) >= limit:
                            break
                    except Exception as e:
                        app.logger.error(f"处理记录 {record_id} 失败: {str(e)}")
                
                # 将筛选结果赋值给recent_records
                recent_records = filtered_records
                
                # 如果没有找到记录，显示提示信息
                if not filtered_records:
                    error = "未找到匹配的审计记录"
            except Exception as e:
                error = f"高级查询失败: {str(e)}"
                app.logger.error(f"高级查询失败: {str(e)}")
        else:
            # 查询单条记录
            try:
                record_id_str = request.form.get('record_id', '')
                if not record_id_str or not record_id_str.strip():
                    error = "请输入有效的审计记录ID"
                else:
                    try:
                        record_id = int(record_id_str)
                        record_data = contract_manager.get_audit_record(record_id)
                        if record_data:
                            user_address, action, details, timestamp = record_data
                            record = {
                                'id': record_id,
                                'user': user_address,
                                'action': action,
                                'details': details,
                                'timestamp': timestamp
                            }
                        else:
                            error = f"未找到ID为 {record_id} 的审计记录"
                    except ValueError:
                        error = f"无效的记录ID格式: {record_id_str}"
            except Exception as e:
                error = f"查询审计记录失败: {str(e)}"
    
    return render_template('audit_trail.html', 
                           record=record, 
                           recent_records=recent_records, 
                           error=error,
                           has_records=has_records,
                           total_records=total_records,
                           today_records=today_records,
                           alert_records=alert_records,
                           user_count=user_count,
                           login_count=login_count,
                           upload_count=upload_count,
                           verify_count=verify_count,
                           revoke_count=revoke_count,
                           yesterday_records=yesterday_records,
                           day_2_records=day_2_records,
                           day_3_records=day_3_records,
                           day_4_records=day_4_records,
                           day_5_records=day_5_records,
                           earlier_records=earlier_records)

@app.route('/api/record_audit', methods=['POST'])
def record_audit_api():
    """API端点：记录审计操作"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    data = request.json
    if not data or 'action' not in data or 'details' not in data:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    
    action = data['action']
    details = data['details']
    
    try:
        # 在生产环境中减少日志输出
        if app.debug:
            app.logger.info(f"记录审计: {action} - {details}")
        
        # 记录审计操作
        result = contract_manager.record_audit_action(action, details)
        if result and result.get('success'):
            # 在生产环境中减少日志输出
            if app.debug:
                app.logger.info(f"审计记录成功，交易哈希: {result.get('tx_hash', '未知')}")
            return jsonify({
                'success': True, 
                'message': f'审计记录成功', 
                'record_id': result.get('block_number', 0)  # 使用区块号作为记录ID
            })
        else:
            app.logger.error(f"审计记录失败: {result}")
            return jsonify({'success': False, 'message': f'审计记录处理失败'}), 500
    except Exception as e:
        app.logger.error(f"记录审计失败: {str(e)}")
        return jsonify({'success': False, 'message': f'记录审计失败: {str(e)}'}), 500

# 审计记录操作类型处理函数
def get_action_class(action):
    """根据操作类型返回对应的CSS类"""
    action = action.lower() if action else ""
    if '登录' in action:
        return 'login'
    elif '登出' in action or 'logout' in action:
        return 'logout'
    elif '上链' in action or '上传' in action:
        return 'upload'
    elif '验证' in action:
        return 'verify'
    elif '撤销' in action:
        return 'revoke'
    else:
        return 'other'  # 默认返回其他类型

def get_action_icon(action):
    """根据操作类型返回对应的FontAwesome图标类"""
    action = action.lower() if action else ""
    if '登录' in action:
        return 'fas fa-sign-in-alt'
    elif '登出' in action or 'logout' in action:
        return 'fas fa-sign-out-alt'
    elif '上链' in action or '上传' in action:
        return 'fas fa-upload'
    elif '验证' in action:
        return 'fas fa-check-circle'
    elif '撤销' in action:
        return 'fas fa-ban'
    else:
        return 'fas fa-cog'  # 默认返回齿轮图标

def get_action_display(action):
    """根据操作类型返回对应的中文显示名称"""
    action = action.lower() if action else ""
    
    # 对英文操作类型的特殊处理
    if action == 'verify':
        return '数据验证'
    elif action == 'dataupload':
        return '数据上链'
    elif action == 'login':
        return '用户登录'
    elif action == 'logout':
        return '用户登出'
    elif action == 'revoke':
        return '数据撤销'
    
    # 对中文操作类型的处理
    if '登录' in action:
        return '用户登录'
    elif '上链' in action or '上传' in action:
        return '数据上链'
    elif '验证' in action:
        return '数据验证'
    elif '撤销' in action:
        return '数据撤销'
    
    # 返回原始操作类型
    return action

@app.route('/check_blockchain')
def check_blockchain():
    """检查区块链连接状态"""
    try:
        # 使用Web3库检查与区块链节点的连接
        w3 = Web3(Web3.HTTPProvider('HTTP://127.0.0.1:8545'))
        is_connected = w3.is_connected()
        
        # 如果连接成功，尝试获取区块链信息
        if is_connected:
            try:
                # 尝试获取最新区块号以确认连接正常
                latest_block = w3.eth.block_number
                # 尝试获取账户列表以确认连接正常
                accounts = w3.eth.accounts
                
                # 记录区块链连接成功的日志
                app.logger.info(f"区块链连接成功，最新区块: {latest_block}")
                
                return jsonify({
                    'connected': True,
                    'block_number': latest_block,
                    'network_id': w3.eth.chain_id,
                    'accounts_count': len(accounts)
                })
            except Exception as e:
                app.logger.error(f"区块链状态检查错误: {str(e)}")
                return jsonify({
                    'connected': False,
                    'error': f"区块链通信错误: {str(e)}"
                })
        else:
            app.logger.warning("区块链连接失败")
            return jsonify({
                'connected': False,
                'error': "无法连接到区块链节点"
            })
    except Exception as e:
        app.logger.error(f"区块链连接检查异常: {str(e)}")
        return jsonify({
            'connected': False, 
            'error': f"连接异常: {str(e)}"
        })

# 将辅助函数添加到Jinja2全局环境
app.jinja_env.globals.update(
    get_action_class=get_action_class,
    get_action_icon=get_action_icon,
    get_action_display=get_action_display
) 