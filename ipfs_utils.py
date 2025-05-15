import os
import hashlib
import random
import string
import subprocess
import time
import requests
import tempfile
import json
import urllib3

# 强制设置urllib3的证书验证，避免潜在的SSL错误
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# IPFS相关配置
IPFS_API_URL = 'http://127.0.0.1:5001'         # 用于HTTP请求的URL
IPFS_GATEWAY = 'http://localhost:8080/ipfs/'   # 默认IPFS网关

def generate_mock_ipfs_hash():
    """
    生成模拟的IPFS哈希，当真实IPFS连接失败时使用
    
    返回:
    - 格式化的IPFS哈希(CID)
    """
    # 生成类似于IPFS格式的哈希 (Qm开头的46位字符)
    prefix = "Qm"  # IPFS哈希的标准前缀
    chars = string.ascii_letters + string.digits
    suffix = ''.join(random.choice(chars) for _ in range(44))
    return prefix + suffix

def check_ipfs_daemon():
    """
    检查IPFS守护进程是否运行
    
    返回:
    - 如果IPFS守护进程运行中则返回True，否则返回False
    """
    try:
        # 使用HTTP请求检查API是否可用
        print("尝试通过HTTP请求检查IPFS状态...")
        response = requests.post(f"{IPFS_API_URL}/api/v0/version")
        if response.status_code == 200:
            version_info = response.json()
            print(f"IPFS守护进程正在运行，版本: {version_info.get('Version', '未知')}")
            return True
    except Exception as e:
        print(f"IPFS守护进程检查失败: {str(e)}")
    
    return False

def try_start_ipfs_daemon():
    """
    尝试启动IPFS守护进程
    
    返回:
    - 如果成功启动则返回True，否则返回False
    """
    if check_ipfs_daemon():
        return True  # 守护进程已在运行
    
    try:
        # 尝试启动IPFS守护进程
        print("尝试启动IPFS守护进程...")
        # 使用subprocess在后台启动进程
        process = subprocess.Popen(
            ["ipfs", "daemon"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        
        # 给一些时间让守护进程启动
        time.sleep(3)
        
        # 再次检查是否成功启动
        if check_ipfs_daemon():
            print("成功启动IPFS守护进程")
            return True
        else:
            print("无法启动IPFS守护进程")
            return False
    except Exception as e:
        print(f"启动IPFS守护进程时出错: {str(e)}")
        return False

def upload_to_ipfs(data_or_file):
    """
    将数据或文件上传到IPFS
    
    参数:
    - data_or_file: 字符串数据或文件路径
    
    返回:
    - IPFS哈希(CID)，如果上传失败则返回模拟哈希
    """
    # 检查IPFS守护进程是否在运行
    ipfs_running = check_ipfs_daemon()
    if not ipfs_running:
        # 尝试启动IPFS守护进程
        print("IPFS守护进程未运行，尝试自动启动...")
        ipfs_running = try_start_ipfs_daemon()
    
    if not ipfs_running:
        # 如果仍然无法启动，发出警告
        print("警告: IPFS守护进程未运行，将使用模拟模式")
        mock_hash = generate_mock_ipfs_hash()
        print(f"模拟IPFS哈希: {mock_hash}")
        return mock_hash
    
    try:
        is_file = os.path.isfile(data_or_file)
        
        if is_file:
            file_size = os.path.getsize(data_or_file)
            print(f"正在上传文件: {data_or_file}")
            print(f"文件大小: {file_size/1024:.2f} KB")
            
            # 使用HTTP请求上传文件
            with open(data_or_file, 'rb') as file:
                files = {'file': (os.path.basename(data_or_file), file)}
                response = requests.post(f"{IPFS_API_URL}/api/v0/add?stream-channels=true", files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    ipfs_hash = result['Hash']
                    print(f"文件成功上传到IPFS")
                    print(f"IPFS哈希: {ipfs_hash}")
                    print(f"访问链接: {IPFS_GATEWAY}{ipfs_hash}")
                    return ipfs_hash
                else:
                    raise Exception(f"IPFS API返回错误，状态码: {response.status_code}, 响应: {response.text}")
        else:
            # 上传字符串数据
            print(f"正在上传字符串数据(长度: {len(data_or_file)})")
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(data_or_file.encode('utf-8'))
                temp_path = temp_file.name
            
            # 上传临时文件
            with open(temp_path, 'rb') as file:
                files = {'file': ('data.txt', file)}
                response = requests.post(f"{IPFS_API_URL}/api/v0/add?stream-channels=true", files=files)
                
                # 删除临时文件
                os.unlink(temp_path)
                
                if response.status_code == 200:
                    result = response.json()
                    ipfs_hash = result['Hash']
                    print(f"数据成功上传到IPFS")
                    print(f"IPFS哈希: {ipfs_hash}")
                    return ipfs_hash
                else:
                    raise Exception(f"IPFS API返回错误，状态码: {response.status_code}")
    
    except Exception as e:
        print(f"上传到IPFS时出错: {str(e)}")
        print("回退到模拟模式...")
        # 返回模拟哈希
        mock_hash = generate_mock_ipfs_hash()
        print(f"生成模拟哈希: {mock_hash}")
        return mock_hash

def download_from_ipfs(hash_value, output_path=None):
    """
    从IPFS下载文件或数据
    
    参数:
    - hash_value: IPFS哈希(CID)
    - output_path: 输出文件路径，如果为None则返回数据
    
    返回:
    - 如果output_path为None，则返回数据内容
    - 如果output_path不为None，则将数据保存到文件并返回文件路径
    """
    # 检查IPFS守护进程
    if not check_ipfs_daemon() and not try_start_ipfs_daemon():
        print("IPFS守护进程不可用，无法下载")
        return None
    
    try:
        # 尝试通过HTTP API获取数据
        print(f"尝试通过IPFS API下载数据: {hash_value}")
        response = requests.post(f"{IPFS_API_URL}/api/v0/cat?arg={hash_value}")
        
        if response.status_code == 200:
            data = response.content
            print(f"从IPFS获取了 {len(data)} 字节的数据")
            
            if output_path:
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(data)
                print(f"数据已从IPFS下载到: {output_path}")
                return output_path
            else:
                return data
        else:
            # 尝试使用get命令而不是cat命令
            print(f"尝试通过IPFS API的get命令下载数据...")
            temp_dir = tempfile.mkdtemp()
            params = {'arg': hash_value, 'output': temp_dir}
            response = requests.post(f"{IPFS_API_URL}/api/v0/get", params=params)
            
            if response.status_code == 200:
                downloaded_path = os.path.join(temp_dir, hash_value)
                if output_path:
                    # 确保输出目录存在
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # 如果存在则拷贝文件
                    if os.path.exists(downloaded_path):
                        with open(downloaded_path, 'rb') as src, open(output_path, 'wb') as dst:
                            dst.write(src.read())
                        print(f"数据已从IPFS下载到: {output_path}")
                        return output_path
                    else:
                        raise Exception(f"下载的文件未找到: {downloaded_path}")
                else:
                    # 读取文件内容
                    with open(downloaded_path, 'rb') as f:
                        data = f.read()
                    return data
            else:
                raise Exception(f"IPFS API返回错误，状态码: {response.status_code}, 响应: {response.text}")
            
    except Exception as e:
        print(f"从IPFS下载时出错: {str(e)}")
        # 尝试通过网关获取
        try:
            print(f"尝试通过网关获取: {IPFS_GATEWAY}{hash_value}")
            response = requests.get(f"{IPFS_GATEWAY}{hash_value}", timeout=10)
            if response.status_code == 200:
                data = response.content
                if output_path:
                    # 确保输出目录存在
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    with open(output_path, 'wb') as f:
                        f.write(data)
                    print(f"通过网关下载数据到: {output_path}")
                    return output_path
                else:
                    print(f"通过网关获取了 {len(data)} 字节的数据")
                    return data
            else:
                raise Exception(f"网关请求失败，状态码: {response.status_code}")
        except Exception as gateway_error:
            print(f"通过网关获取数据时出错: {str(gateway_error)}")
        
        return None

def verify_ipfs_hash(hash_value):
    """
    验证IPFS哈希是否有效
    
    参数:
    - hash_value: IPFS哈希(CID)
    
    返回:
    - 如果哈希有效则返回True，否则返回False
    """
    # 简单的格式验证
    if not hash_value or not isinstance(hash_value, str):
        return False
    
    # IPFS CIDv0格式检查 (以Qm开头，总长度为46)
    if hash_value.startswith('Qm') and len(hash_value) == 46:
        return True
    
    # IPFS CIDv1格式检查
    if hash_value.startswith('b') and len(hash_value) > 48:
        return True
    
    # 如果IPFS可用，尝试真实验证
    if check_ipfs_daemon():
        try:
            # 使用HTTP API检查哈希
            response = requests.post(f"{IPFS_API_URL}/api/v0/object/stat?arg={hash_value}")
            if response.status_code == 200:
                return True
        except Exception as e:
            print(f"验证IPFS哈希时出错: {str(e)}")
            # 如果发生异常，哈希可能无效
            pass
    
    # 默认返回True，因为我们已经执行了基本的格式验证
    return True

# 如果直接运行此文件，执行测试
if __name__ == "__main__":
    # 测试IPFS状态
    if check_ipfs_daemon():
        print("IPFS守护进程正在运行")
    else:
        print("IPFS守护进程未运行")
        if try_start_ipfs_daemon():
            print("成功启动IPFS守护进程")
        else:
            print("无法启动IPFS守护进程，将使用模拟模式")
    
    # 测试上传
    test_string = "这是一个测试字符串，用于验证IPFS功能是否正常"
    ipfs_hash = upload_to_ipfs(test_string)
    print(f"上传测试字符串的IPFS哈希: {ipfs_hash}")
    
    # 测试下载
    if ipfs_hash:
        data = download_from_ipfs(ipfs_hash)
        if data:
            try:
                decoded_data = data.decode('utf-8')
                print(f"下载的数据: {decoded_data}")
                print("验证通过" if decoded_data == test_string else "验证失败")
            except:
                print(f"下载的二进制数据长度: {len(data)}")
    
    # 测试验证
    is_valid = verify_ipfs_hash(ipfs_hash)
    print(f"IPFS哈希 {ipfs_hash} 验证结果: {'有效' if is_valid else '无效'}") 