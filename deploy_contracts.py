"""
智能合约部署和测试脚本

此脚本用于部署警情链系统的智能合约，并进行基本测试。
"""

import os
import sys
import json
import time
from web3 import Web3
import contract_manager as cm
import compile_with_viaIR

def main():
    """主函数"""
    print("=== 警情链智能合约部署工具 ===")
    
    # 检查Web3连接
    w3 = Web3(Web3.HTTPProvider('HTTP://127.0.0.1:8545'))
    if not w3.is_connected():
        print("错误: 无法连接到以太坊节点。请确保本地以太坊节点(如Ganache)正在运行。")
        sys.exit(1)
    
    print(f"连接到以太坊节点成功!")
    print(f"当前区块号: {w3.eth.block_number}")
    print(f"可用账户: {w3.eth.accounts[:3]}...")
    
    # 确保contracts目录存在
    os.makedirs('contracts', exist_ok=True)
    
    # 先编译合约
    print("\n=== 预编译智能合约 ===")
    try:
        # 编译PoliceRecordContract
        police_contract_path = os.path.join('contracts', 'PoliceRecordContract.sol')
        if os.path.exists(police_contract_path):
            compile_with_viaIR.compile_contract_with_viaIR(police_contract_path)
        
        # 编译AuditTrailContract
        audit_contract_path = os.path.join('contracts', 'AuditTrailContract.sol')
        if os.path.exists(audit_contract_path):
            compile_with_viaIR.compile_contract_with_viaIR(audit_contract_path)
        
        print("预编译完成!")
    except Exception as e:
        print(f"预编译失败: {str(e)}")
        sys.exit(1)
    
    # 检查是否已有部署的合约
    address_file = os.path.join('contracts', 'contract_addresses.json')
    if os.path.exists(address_file):
        try:
            with open(address_file, 'r') as f:
                addresses = json.load(f)
            print(f"发现已部署的合约地址: {addresses}")
            choice = input("已存在已部署的合约。是否重新部署? (y/n): ")
            if choice.lower() != 'y':
                print("使用现有合约地址。")
                run_tests()
                return
        except Exception as e:
            print(f"读取合约地址文件失败: {str(e)}")
    
    # 开始部署合约
    print("\n=== 开始部署智能合约 ===")
    
    try:
        # 部署警情记录合约
        print("\n部署警情记录合约...")
        police_contract = cm.deploy_police_record_contract()
        print("警情记录合约部署成功!")
        
        # 部署审计跟踪合约
        print("\n部署审计跟踪合约...")
        audit_contract = cm.deploy_audit_trail_contract()
        print("审计跟踪合约部署成功!")
        
        # 记录部署操作
        print("\n记录合约部署操作...")
        cm.record_audit_action("ContractDeployment", "初始化部署智能合约")
        print("审计记录已添加!")
        
        print("\n所有合约部署成功!")
        
        # 运行测试
        run_tests()
        
    except Exception as e:
        print(f"合约部署失败: {str(e)}")
        sys.exit(1)

def run_tests():
    """运行智能合约测试"""
    print("\n=== 开始测试智能合约 ===")
    
    try:
        # 测试数据
        test_police_no = f"TEST{int(time.time())}"
        test_data = {
            "police_no": test_police_no,
            "receive_time": "2024-06-05 10:00:00",
            "police_officer": "测试警官",
            "result": "测试处理结果",
            "gps_location": "39.915119,116.403963",
            "pdf_hash": "ab123456789012345678901234567890",
            "merkle_hash": "cd123456789012345678901234567890",
            "ipfs_hash": "Qm123456789012345678901234567890"
        }
        
        # 测试1：添加警情记录
        print("\n测试1: 添加警情记录")
        result = cm.add_police_record(
            test_data["police_no"],
            test_data["receive_time"],
            test_data["police_officer"],
            test_data["result"],
            test_data["gps_location"],
            test_data["pdf_hash"],
            test_data["merkle_hash"],
            test_data["ipfs_hash"]
        )
        
        if result['success']:
            print(f"警情记录添加成功!")
            print(f"交易哈希: {result['tx_hash']}")
            print(f"区块号: {result['block_number']}")
        else:
            print(f"警情记录添加失败: {result.get('error', '未知错误')}")
            return
        
        # 测试2：获取警情记录
        print("\n测试2: 获取警情记录")
        record = cm.get_police_record(test_data["police_no"])
        print(f"获取到记录: {record}")
        
        # 测试3：验证警情记录
        print("\n测试3: 验证警情记录")
        verification = cm.verify_police_record(test_data["police_no"], test_data["pdf_hash"])
        print(f"验证结果: {verification}")
        
        # 测试4：添加审计记录
        print("\n测试4: 添加审计记录")
        audit_result = cm.record_audit_action("TestAction", f"测试警情记录: {test_police_no}")
        print(f"审计记录添加成功: {audit_result}")
        
        # 测试5：获取审计记录
        print("\n测试5: 获取最近的审计记录")
        recent_records = cm.get_recent_audit_records(5)
        print(f"最近的审计记录IDs: {recent_records}")
        
        if len(recent_records) > 0:
            record_id = recent_records[0]
            record = cm.get_audit_record(record_id)
            print(f"审计记录详情: {record}")
        
        # 测试6：撤销警情记录
        print("\n测试6: 撤销警情记录")
        revoke_result = cm.revoke_police_record(test_police_no, "测试撤销")
        print(f"撤销结果: {revoke_result}")
        
        # 测试7：验证撤销后的记录
        print("\n测试7: 验证撤销后的记录")
        verification = cm.verify_police_record(test_data["police_no"], test_data["pdf_hash"])
        print(f"撤销后的验证结果: {verification}")
        
        print("\n所有测试完成!")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == "__main__":
    main() 