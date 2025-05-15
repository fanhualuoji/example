"""
智能合约管理模块

此模块负责智能合约的编译、部署和交互。
它提供了一个统一的接口，供其他模块调用合约功能。
"""

import os
import json
import time
from web3 import Web3
from solcx import compile_source, install_solc
from web3.middleware import geth_poa_middleware
import compile_with_viaIR as compiler
from eth_account import Account
from dotenv import load_dotenv

# 尝试加载solcx
try:
    import solcx
    # 尝试安装Solidity编译器
    try:
        install_solc('0.8.17')
    except Exception as e:
        print(f"安装Solidity编译器失败: {str(e)}")
except ImportError:
    print("警告: solcx库不可用，无法编译合约。请安装solcx库: pip install py-solc-x")

class ContractManager:
    """智能合约管理类"""
    
    def __init__(self):
        self.config = self._load_config()
        self.setup_web3()
        
        self.contract_dir = os.path.join(os.getcwd(), 'contracts')
        self.compiled_contracts = {}
        self.deployed_contracts = {}
        self.contract_addresses = {}
        
        # 尝试加载已部署的合约地址
        self._load_contract_addresses()
        
        print(f"合约管理器初始化，连接状态: {'已连接' if self.w3.is_connected() else '未连接'}")
        if self.w3.is_connected():
            print(f"当前区块号: {self.w3.eth.block_number}")
            print(f"可用账户: {self.w3.eth.accounts[:3]}...")
    
    def _load_config(self):
        try:
            load_dotenv()  # 加载环境变量
            with open('config/config.json', 'r') as f:
                config = json.load(f)
                # 从环境变量获取私钥
                config['blockchain']['private_key'] = os.getenv('PRIVATE_KEY')
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
            
    def setup_web3(self):
        try:
            network_config = self.config['blockchain']
            self.w3 = Web3(Web3.HTTPProvider(network_config['rpc_url']))
            self.chain_id = network_config['chain_id']
            
            # 使用私钥创建账户
            private_key = network_config['private_key']
            self.account = Account.from_key(private_key)
            
            print(f"Connected to network: {network_config['network']}")
            print(f"Account address: {self.account.address}")
        except Exception as e:
            print(f"Error setting up web3: {e}")
        
    def _load_contract_addresses(self):
        """加载已部署的合约地址，支持多个区块链网络"""
        address_file = os.path.join(self.contract_dir, 'contract_addresses.json')
        if os.path.exists(address_file):
            try:
                with open(address_file, 'r') as f:
                    all_addresses = json.load(f)
                
                # 获取当前网络ID作为键
                network_id = str(self.chain_id)
                network_name = self.config['blockchain']['network']
                network_key = f"{network_name}_{network_id}"
                
                print(f"当前网络: {network_name} (ID: {network_id})")
                
                # 检查是否有当前网络的合约地址
                if network_key in all_addresses:
                    self.contract_addresses = all_addresses[network_key]
                    print(f"已加载网络 {network_key} 的合约地址: {self.contract_addresses}")
                else:
                    print(f"未找到网络 {network_key} 的合约地址")
                    self.contract_addresses = {}
            except Exception as e:
                print(f"加载合约地址文件失败: {str(e)}")
                self.contract_addresses = {}
    
    def _save_contract_addresses(self):
        """保存已部署的合约地址，支持多个区块链网络"""
        os.makedirs(self.contract_dir, exist_ok=True)
        address_file = os.path.join(self.contract_dir, 'contract_addresses.json')
        
        # 获取当前网络ID作为键
        network_id = str(self.chain_id)
        network_name = self.config['blockchain']['network']
        network_key = f"{network_name}_{network_id}"
        
        # 读取现有的地址文件
        all_addresses = {}
        if os.path.exists(address_file):
            try:
                with open(address_file, 'r') as f:
                    all_addresses = json.load(f)
            except Exception as e:
                print(f"读取现有合约地址文件失败: {str(e)}")
        
        # 更新当前网络的合约地址
        all_addresses[network_key] = self.contract_addresses
        
        try:
            with open(address_file, 'w') as f:
                json.dump(all_addresses, f, indent=2)
            print(f"已保存网络 {network_key} 的合约地址")
        except Exception as e:
            print(f"保存合约地址文件失败: {str(e)}")
    
    def compile_contract(self, contract_name):
        """
        编译智能合约
        
        Args:
            contract_name: 合约名称（不包含.sol扩展名）
            
        Returns:
            编译后的合约接口
        """
        if not self.w3.is_connected():
            raise ConnectionError("无法连接到以太坊节点")
        
        contract_path = os.path.join(self.contract_dir, f"{contract_name}.sol")
        
        if not os.path.exists(contract_path):
            raise FileNotFoundError(f"合约文件不存在: {contract_path}")
        
        print(f"编译合约: {contract_name}")
        
        try:
            # 使用我们的自定义编译器，支持--via-ir选项
            contract_interface = compiler.compile_contract_with_viaIR(contract_path)
            
            self.compiled_contracts[contract_name] = contract_interface
            print(f"合约 {contract_name} 编译成功")
            
            return contract_interface
        except Exception as e:
            print(f"编译合约 {contract_name} 失败: {str(e)}")
            raise
    
    def deploy_contract(self, contract_name, *args, account_index=0, gas_limit=5000000):
        """
        部署智能合约
        
        Args:
            contract_name: 合约名称
            *args: 传递给合约构造函数的参数
            account_index: 用于部署的账户索引
            gas_limit: 部署合约的gas限制
            
        Returns:
            已部署的合约实例
        """
        if not self.w3.is_connected():
            raise ConnectionError("无法连接到以太坊节点")
        
        print(f"部署合约: {contract_name}")
        
        # 如果合约尚未编译，先编译
        if contract_name not in self.compiled_contracts:
            self.compile_contract(contract_name)
        
        # 获取合约接口
        contract_interface = self.compiled_contracts[contract_name]
        
        # 创建合约对象
        contract = self.w3.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bin']
        )
        
        # 获取账户地址
        if account_index >= len(self.w3.eth.accounts):
            raise ValueError(f"账户索引超出范围，最大索引为 {len(self.w3.eth.accounts) - 1}")
        
        account = self.w3.eth.accounts[account_index]
        print(f"使用账户 {account} 部署合约")
        
        try:
            # 估算gas
            # 构造合约部署交易
            tx_hash = contract.constructor(*args).transact({
                'from': account,
                'gas': gas_limit
            })
            
            # 等待交易确认
            print("等待交易确认...")
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            contract_address = tx_receipt.contractAddress
            print(f"合约已部署到地址: {contract_address}")
            
            # 创建合约实例
            contract_instance = self.w3.eth.contract(
                address=contract_address,
                abi=contract_interface['abi']
            )
            
            # 保存合约实例和地址
            self.deployed_contracts[contract_name] = contract_instance
            self.contract_addresses[contract_name] = contract_address
            
            # 保存合约地址到文件
            self._save_contract_addresses()
            
            return contract_instance
        
        except Exception as e:
            print(f"部署合约 {contract_name} 失败: {str(e)}")
            raise
    
    def get_contract(self, contract_name):
        """
        获取已部署的合约实例
        
        Args:
            contract_name: 合约名称
            
        Returns:
            合约实例
        """
        # 检查是否已有缓存的合约实例
        if contract_name in self.deployed_contracts:
            return self.deployed_contracts[contract_name]
        
        # 检查是否有已知的合约地址
        if contract_name not in self.contract_addresses:
            raise ValueError(f"未找到合约 {contract_name} 的地址")
        
        contract_address = self.contract_addresses[contract_name]
        
        # 如果合约未编译，先编译
        if contract_name not in self.compiled_contracts:
            self.compile_contract(contract_name)
        
        # 获取合约接口
        contract_interface = self.compiled_contracts[contract_name]
        
        # 创建合约实例
        contract_instance = self.w3.eth.contract(
            address=contract_address,
            abi=contract_interface['abi']
        )
        
        # 缓存合约实例
        self.deployed_contracts[contract_name] = contract_instance
        
        return contract_instance
    
    def call_contract_function(self, contract_name, function_name, *args):
        """调用合约函数（只读）

        Args:
            contract_name: 合约名称
            function_name: 函数名称
            *args: 函数参数

        Returns:
            函数返回值
        """
        try:
            # 获取合约实例
            if isinstance(contract_name, str):
                contract = self.get_contract(contract_name)
            else:
                # 如果已经是合约实例，直接使用
                contract = contract_name
            
            # 确保contract是合约对象而不是字符串
            if not hasattr(contract, 'functions'):
                raise ValueError(f"无效的合约对象: {type(contract)}")
            
            # 获取合约函数
            contract_function = getattr(contract.functions, function_name)
            
            # 调用函数
            result = contract_function(*args).call()
            return result
        except Exception as e:
            print(f"Error in contract function call: {e}")
            return None
    
    def send_contract_transaction(self, contract_name, function_name, *args, account_index=0, gas_limit=2000000):
        """
        发送合约写入交易
        
        Args:
            contract_name: 合约名称
            function_name: 函数名称
            *args: 函数参数
            account_index: 发送者账户索引
            gas_limit: gas限制（默认值增加到2000000）
            
        Returns:
            交易哈希和交易收据
        """
        if not self.w3.is_connected():
            raise ConnectionError("无法连接到以太坊节点")
        
        contract = self.get_contract(contract_name)
        account = self.w3.eth.accounts[account_index]
        
        # 获取函数对象
        contract_function = getattr(contract.functions, function_name)
        
        try:
            # 发送交易
            tx_hash = contract_function(*args).transact({
                'from': account,
                'gas': gas_limit
            })
            
            # 等待交易确认
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # 打印交易信息
            print(f"交易已确认: {tx_hash.hex()}")
            print(f"区块号: {tx_receipt.blockNumber}")
            print(f"使用的gas: {tx_receipt.gasUsed}")
            
            return {
                'tx_hash': tx_hash.hex(),
                'block_number': tx_receipt.blockNumber,
                'gas_used': tx_receipt.gasUsed,
                'success': tx_receipt.status == 1
            }
            
        except Exception as e:
            print(f"发送交易失败: {str(e)}")
            raise
    
    def get_contract_events(self, contract_name, event_name, from_block=0, to_block='latest'):
        """
        获取合约事件
        
        Args:
            contract_name: 合约名称
            event_name: 事件名称
            from_block: 起始区块
            to_block: 结束区块
            
        Returns:
            事件列表
        """
        contract = self.get_contract(contract_name)
        
        # 获取事件过滤器
        event_filter = getattr(contract.events, event_name).createFilter(
            fromBlock=from_block,
            toBlock=to_block
        )
        
        # 获取事件
        events = event_filter.get_all_entries()
        
        return events

# 创建合约管理器单例
contract_manager = ContractManager()

# 导出主要函数，方便其他模块调用
def deploy_police_record_contract():
    """部署警情记录合约"""
    return contract_manager.deploy_contract('PoliceRecordContract')

def deploy_audit_trail_contract():
    """部署审计跟踪合约"""
    return contract_manager.deploy_contract('AuditTrailContract')

def add_police_record(police_no, receive_time, police_officer, result, gps_location, pdf_hash, merkle_hash, ipfs_hash, account_index=0):
    """添加警情记录到区块链"""
    return contract_manager.send_contract_transaction(
        'PoliceRecordContract', 
        'addRecord',
        police_no, 
        receive_time, 
        police_officer, 
        result, 
        gps_location, 
        pdf_hash, 
        merkle_hash, 
        ipfs_hash,
        account_index=account_index
    )

def revoke_police_record(police_no, reason, account_index=0):
    """撤销警情记录"""
    return contract_manager.send_contract_transaction(
        'PoliceRecordContract', 
        'revokeRecord',
        police_no, 
        reason,
        account_index=account_index
    )

def verify_police_record(police_no, pdf_hash):
    """验证警情记录的有效性和完整性"""
    try:
        # 获取合约实例
        contract = contract_manager.get_contract('PoliceRecordContract')
        
        print(f"开始验证警情记录: {police_no}")
        
        # 使用getRecordStatus函数代替recordExists和isRecordActive
        try:
            # 获取记录状态
            exists, is_active = contract.functions.getRecordStatus(police_no).call()
            print(f"记录状态: 存在={exists}, 有效={is_active}")
            
            if not exists:
                return {'exists': False, 'active': False, 'hash_match': False, 'verified': False}
            
            # 获取记录哈希信息
            pdf_hash_stored, merkle_hash, ipfs_hash, timestamp = contract.functions.getRecordHashes(police_no).call()
            
            # 格式化哈希值 - 确保统一小写格式并移除可能的前缀
            pdf_hash_stored = pdf_hash_stored.lower().strip() if pdf_hash_stored else ""
            if pdf_hash:
                pdf_hash = pdf_hash.lower().strip()
                # 移除可能的0x前缀
                if pdf_hash.startswith("0x"):
                    pdf_hash = pdf_hash[2:]
            else:
                pdf_hash = ""
            
            print(f"存储的PDF哈希: {pdf_hash_stored}")
            print(f"当前PDF哈希: {pdf_hash}")
            
            # 比较哈希值 - 如果存储的哈希为空或未提供当前哈希，则跳过哈希检查
            if not pdf_hash_stored:
                print("警告: 区块链上存储的PDF哈希为空，跳过哈希验证")
                hash_match = True  # 如果区块链上没有存储哈希，则不进行哈希比对
            elif not pdf_hash:
                print("警告: 未提供当前PDF哈希，跳过哈希验证")
                hash_match = True  # 如果未提供当前哈希，则不进行哈希比对
            else:
                hash_match = pdf_hash_stored == pdf_hash
                print(f"哈希比对结果: {'匹配' if hash_match else '不匹配'}")
                if not hash_match:
                    print(f"哈希不匹配的原因可能是:")
                    print(f"  1. PDF内容已被修改")
                    print(f"  2. 哈希计算方法不一致")
                    print(f"  3. 上链时使用了不同的PDF版本")
                    print(f"存储的哈希长度: {len(pdf_hash_stored)}, 当前哈希长度: {len(pdf_hash)}")
            
            result = {
                'exists': exists,
                'active': is_active, 
                'hash_match': hash_match,
                'verified': exists and is_active and hash_match
            }
            
            return result
        except Exception as contract_error:
            print(f"调用合约函数失败: {contract_error}")
            
            # 尝试使用旧方法(verifyRecord)验证
            try:
                print("尝试使用verifyRecord函数验证...")
                verification_result = contract.functions.verifyRecord(police_no, pdf_hash).call()
                
                # 处理可能返回3个或4个值的情况
                if isinstance(verification_result, tuple):
                    if len(verification_result) >= 3:
                        exists = verification_result[0]
                        active = verification_result[1]
                        hash_match = verification_result[2]
                        
                        return {
                            'exists': exists,
                            'active': active,
                            'hash_match': hash_match,
                            'verified': exists and active and hash_match
                        }
                elif isinstance(verification_result, bool):
                    return {
                        'exists': True,
                        'active': True,
                        'hash_match': verification_result,
                        'verified': verification_result
                    }
                else:
                    print(f"意外的验证结果格式: {verification_result}")
                    return {'exists': False, 'active': False, 'hash_match': False, 'verified': False}
            except Exception as e2:
                print(f"verifyRecord调用也失败: {e2}")
                raise
    except Exception as e:
        print(f"验证警情记录失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'exists': False,
            'active': False,
            'hash_match': False,
            'verified': False,
            'error': str(e)
        }

def get_police_record(police_no):
    """获取警情记录详情"""
    try:
        print(f"尝试获取警情记录: {police_no}")
        
        # 获取合约实例
        contract = contract_manager.get_contract('PoliceRecordContract')
        
        # 检查记录状态
        try:
            # 首先验证记录是否存在
            exists, is_active = contract.functions.getRecordStatus(police_no).call()
            print(f"记录状态: 存在={exists}, 有效={is_active}")
            
            if not exists:
                print(f"警情记录 {police_no} 不存在")
                return None
            
            # 获取基本信息
            try:
                basic_info = contract.functions.getRecordBasic(police_no).call()
                receive_time, officer, result, gps_location, is_active = basic_info
                print(f"基本信息获取成功")
            except Exception as e:
                print(f"获取基本信息失败: {e}")
                return None
            
            # 获取哈希信息
            try:
                hash_info = contract.functions.getRecordHashes(police_no).call()
                pdf_hash, merkle_hash, ipfs_hash, timestamp = hash_info
                print(f"哈希信息获取成功")
            except Exception as e:
                print(f"获取哈希信息失败: {e}")
                return None
            
            # 整合所有信息
            return {
                'policeNo': police_no,
                'receiveTime': receive_time,
                'policeOfficer': officer,
                'result': result,
                'gpsLocation': gps_location,
                'pdfHash': pdf_hash,
                'merkleHash': merkle_hash,
                'ipfsHash': ipfs_hash,
                'timestamp': timestamp,
                'isActive': is_active
            }
        except Exception as e:
            print(f"合约函数调用失败: {e}")
            
            # 尝试使用旧方法
            try:
                print("尝试使用getRecord函数获取完整记录...")
                record = contract.functions.getRecord(police_no).call()
                
                return {
                    'policeNo': police_no,
                    'receiveTime': record[0],
                    'policeOfficer': record[1],
                    'result': record[2],
                    'gpsLocation': record[3],
                    'pdfHash': record[4],
                    'merkleHash': record[5],
                    'ipfsHash': record[6],
                    'timestamp': record[7],
                    'isActive': record[8]
                }
            except Exception as e2:
                print(f"使用旧函数获取警情记录也失败: {e2}")
                return None
    except Exception as e:
        print(f"获取警情记录过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def record_audit_action(action, details, account_index=0):
    """记录审计操作"""
    return contract_manager.send_contract_transaction(
        'AuditTrailContract', 
        'recordAction',
        action, 
        details,
        account_index=account_index
    )

def get_audit_record(record_id):
    """获取审计记录详情"""
    try:
        result = contract_manager.call_contract_function(
            'AuditTrailContract', 
            'getAuditRecord',
            record_id
        )
        return result
    except Exception as e:
        print(f"获取审计记录失败: {e}")
        return None

def get_recent_audit_records(count):
    """获取最近的审计记录"""
    try:
        result = contract_manager.call_contract_function(
            'AuditTrailContract', 
            'getRecentRecords',
            count
        )
        return result
    except Exception as e:
        print(f"获取最近审计记录失败: {e}")
        return []

def get_audit_trail_count():
    """获取审计记录总数"""
    try:
        result = contract_manager.call_contract_function(
            'AuditTrailContract', 
            'getAuditTrailCount'
        )
        return result
    except Exception as e:
        print(f"获取审计记录总数失败: {e}")
        return 0 