# 文件名: test_fisco_connection.py
# 功能: 测试Windows系统连接Linux虚拟机上的FISCO BCOS节点

# 导入必要的库
import sys
import os
import json
import time
from client.bcosclient import BcosClient
from client.stattool import StatTool
from client.datatype_parser import DatatypeParser
from client.common.compiler import Compiler
from client_config import client_config

# 彩色输出函数，让错误和成功信息更加醒目
def print_red(msg):
    print(f"\033[91m{msg}\033[0m")

def print_green(msg):
    print(f"\033[92m{msg}\033[0m")

def print_yellow(msg):
    print(f"\033[93m{msg}\033[0m")

def print_blue(msg):
    print(f"\033[94m{msg}\033[0m")

def print_header(title):
    print("\n" + "="*50)
    print_blue(f"  {title}")
    print("="*50)

def check_connection():
    print_header("FISCO BCOS连接测试工具")
    
    # 打印当前配置信息
    print_yellow("当前配置信息:")
    print(f"通信协议: {client_config.client_protocol}")
    if client_config.client_protocol == client_config.PROTOCOL_CHANNEL:
        print(f"连接地址: {client_config.channel_host}:{client_config.channel_port}")
        print(f"证书文件: {client_config.channel_ca}")
        print(f"SDK证书: {client_config.channel_node_cert}")
        print(f"SDK密钥: {client_config.channel_node_key}")
    else:
        print(f"RPC地址: {client_config.remote_rpcurl}")
    
    print(f"链ID: {client_config.fiscoChainId}")
    print(f"群组ID: {client_config.groupid}")
    print(f"Solidity编译器: {client_config.solc_path}")
    
    print_yellow("\n开始测试连接...")
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 初始化BcosClient
        print("1. 初始化FISCO BCOS客户端...", end="")
        client = BcosClient()
        print_green(" 成功")
        
        # 测试1: 获取节点信息
        print("2. 获取节点连接信息...", end="")
        peers = client.getPeers()
        print_green(" 成功")
        print(f"   > 已连接节点数: {len(peers)}")
        for i, peer in enumerate(peers):
            print(f"   > 节点{i+1}: {peer.get('IPAndPort', 'Unknown')}")
        
        # 测试2: 获取区块高度
        print("3. 获取当前区块高度...", end="")
        block_number = client.getBlockNumber()
        print_green(" 成功")
        print(f"   > 当前区块高度: {block_number}")
        
        # 测试3: 获取群组信息
        print("4. 获取群组列表...", end="")
        groups = client.getGroupList()
        print_green(" 成功")
        print(f"   > 群组列表: {groups}")
        
        # 测试4: 获取系统配置
        print("5. 获取系统配置...", end="")
        sys_config = client.getSystemConfigByKey("tx_count_limit")
        print_green(" 成功")
        print(f"   > 交易数量限制: {sys_config}")
        
        # 测试5: 获取节点版本
        print("6. 获取节点版本...", end="")
        version = client.getClientVersion()
        print_green(" 成功")
        print(f"   > 节点信息: {version.get('FISCO-BCOS Version', 'Unknown')}")
        
        # 测试6: 获取最新区块信息
        print("7. 获取最新区块信息...", end="")
        if block_number > 0:
            latest_block = client.getBlockByNumber(block_number)
            print_green(" 成功")
            print(f"   > 区块哈希: {latest_block.get('hash', 'Unknown')}")
            txs = latest_block.get("transactions", [])
            print(f"   > 区块内交易数: {len(txs)}")
        else:
            print_yellow(" 跳过 (当前无区块)")
        
        # 计算测试用时
        end_time = time.time()
        duration = end_time - start_time
        
        print_header("测试结果")
        print_green(f"所有连接测试成功完成! 用时: {duration:.2f}秒")
        print_green("Windows系统已成功连接Linux上的FISCO BCOS节点!")
        print_blue("\n可以开始将项目集成到FISCO BCOS区块链中了")
        
    except Exception as e:
        print_red(f" 失败\n连接测试出错: {str(e)}")
        print_header("错误排查建议")
        print_yellow("1. 检查Linux虚拟机IP地址是否正确，并确保Windows能ping通该IP")
        print_yellow("2. 确认FISCO BCOS节点在Linux上正常运行")
        print_yellow(f"3. 确认证书路径正确: {client_config.channel_ca}")
        print_yellow("4. 检查防火墙是否允许{client_config.channel_port}端口通信")
        print_yellow("5. 确认群组ID和链ID配置正确")
        print_yellow("6. 尝试在Linux上执行相同的测试脚本检查节点状态")
        return False
    finally:
        # 确保客户端正常关闭
        if 'client' in locals():
            client.finish()
    
    return True

if __name__ == "__main__":
    check_connection()