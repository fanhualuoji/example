import sys
import json
import os
from web3 import Web3, HTTPProvider
from web3.eth import Eth
import contract_manager as cm

# 初始化Web3连接
w3 = Web3(HTTPProvider('HTTP://127.0.0.1:8545'))
eth = Eth(w3)
accounts = w3.eth.accounts

# 输出区块链连接状态
print("已连接:", w3.is_connected())
print("可用账户:", w3.eth.accounts)
print("最新区块号:", w3.eth.block_number)

# 检查是否连接成功
if not w3.is_connected():
    print("区块链连接失败！")
    sys.exit(1)
else:
    print("区块链连接成功！")

# 合约部署和状态管理
def initialize_contracts():
    """初始化智能合约，支持多个区块链网络"""
    # 获取当前网络信息
    try:
        network_id = w3.eth.chain_id
        print(f"当前连接的区块链网络ID: {network_id}")
    except Exception as e:
        print(f"无法获取网络ID: {str(e)}")
        network_id = "unknown"

    # 检查是否已经部署了合约
    contracts_deployed = False
    address_file = os.path.join('contracts', 'contract_addresses.json')
    
    if os.path.exists(address_file):
        try:
            with open(address_file, 'r') as f:
                all_addresses = json.load(f)
            
            # 尝试从配置文件获取网络名称
            try:
                with open('config/config.json', 'r') as f:
                    config = json.load(f)
                network_name = config['blockchain']['network']
            except Exception:
                network_name = "default"
            
            # 构建网络键
            network_key = f"{network_name}_{network_id}"
            print(f"寻找网络 {network_key} 的合约地址")
            
            # 检查当前网络是否有已部署的合约
            if network_key in all_addresses:
                network_addresses = all_addresses[network_key]
                if 'PoliceRecordContract' in network_addresses and 'AuditTrailContract' in network_addresses:
                    contracts_deployed = True
                    print(f"已找到网络 {network_key} 的合约地址: {network_addresses}")
            else:
                print(f"未找到网络 {network_key} 的已部署合约")
        except Exception as e:
            print(f"读取合约地址文件失败: {str(e)}")
    
    if not contracts_deployed:
        print(f"在当前网络上未找到已部署的合约，开始部署新合约...")
        try:
            # 部署警情记录合约
            police_contract = cm.deploy_police_record_contract()
            print(f"警情记录合约已部署")
            
            # 部署审计跟踪合约
            audit_contract = cm.deploy_audit_trail_contract()
            print(f"审计跟踪合约已部署")
            
            # 记录合约部署的审计信息
            cm.record_audit_action("ContractDeployment", "部署智能合约")
            
            return True
        except Exception as e:
            print(f"合约部署失败: {str(e)}")
            return False
    
    return True

def save_data_on_block(data):
    """
    将数据保存到区块链
    使用智能合约存储数据，不再支持传统模式和模拟模式
    """
    try:
        # 解析数据获取警情信息
        print("使用智能合约将数据保存到区块链...")
        police_data = json.loads(data)
        police_no = police_data.get('PoliceNo', '')
        receive_time = police_data.get('ReceiveTime', '')
        police_officer = police_data.get('PoliceOfficer', '')
        result = police_data.get('Result', '')
        gps_location = police_data.get('GPSLocation', '')
        pdf_hash = police_data.get('PDF_Hash', '')
        merkle_hash = police_data.get('Merkel_Tophash', '')
        ipfs_hash = police_data.get('IPFS', '')
        
        print(f"警情编号: {police_no}")
        print(f"接警时间: {receive_time}")
        print(f"处警人员: {police_officer}")
        
        try:
            # 将数据添加到智能合约
            result = cm.add_police_record(
                police_no,
                receive_time,
                police_officer,
                result,
                gps_location,
                pdf_hash,
                merkle_hash,
                ipfs_hash
            )
            
            # 记录审计日志
            cm.record_audit_action("DataUpload", f"上传警情记录: {police_no}")
            
            print(f"数据已成功保存到智能合约，区块号: {result['block_number']}")
            
            # 返回结果字典
            return {
                'success': True,
                'message': '上链成功',
                'is_duplicate': False,
                'block_number': result['block_number']
            }
        
        except Exception as contract_error:
            error_str = str(contract_error)
            # 检查是否是因为记录已存在导致的错误
            if "Record already exists" in error_str:
                print("警告: 记录已存在于区块链，请勿重复上链")
                
                # 尝试获取已存在记录的信息
                try:
                    record = get_police_record(police_no)
                    if record and 'timestamp' in record:
                        # 如果能获取到记录，返回已存在的区块信息
                        return {
                            'success': False,
                            'message': '警情记录已存在区块链上，请勿重复上链',
                            'is_duplicate': True,
                            'block_number': record.get('block_number', 0),  # 返回原始区块号
                            'original_record': record  # 返回完整记录
                        }
                except:
                    pass
                
                # 如果无法获取已存在的记录信息，使用通用返回
                return {
                    'success': False,
                    'message': '警情记录已存在区块链上，请勿重复上链',
                    'is_duplicate': True,
                    'block_number': 0  # 不返回临时区块号
                }
            else:
                # 其他类型的错误，重新抛出异常
                raise
    
    except Exception as e:
        print(f"通过智能合约保存数据失败: {str(e)}")
        raise Exception(f"数据上链失败: {str(e)}")

def get_block_info(blocknumber):
    """
    基于区块号从区块链中获取指定区块的相关信息
    注意：此函数已被智能合约替代，但为了向后兼容保留此接口
    """
    try:
        # 通过合约获取该区块包含的交易对应的警情记录
        # 注：这里需要先从区块中找到警情编号，然后通过编号查询完整记录
        # 下面的实现假设我们可以从区块中找到警情编号
        
        # 获取区块中的交易
        block_info = w3.eth.get_block(blocknumber)
        
        if len(block_info["transactions"]) > 0:
            tx = w3.to_hex(block_info["transactions"][0])
            trans_detail = w3.eth.get_transaction(tx)
            
            # 尝试从交易数据中解析出警情编号
            try:
                data = w3.to_text(trans_detail["input"])
                data_json = json.loads(data)
                police_no = data_json.get('PoliceNo', '')
                
                if police_no:
                    # 通过智能合约获取警情记录
                    record = cm.get_police_record(police_no)
                    return json.dumps(data_json)  # 保持与原函数相同的返回格式
                else:
                    return w3.to_text(trans_detail["input"])
            except:
                return w3.to_text(trans_detail["input"])
        
        return "无法从区块中获取数据"
    
    except Exception as e:
        print(f"获取区块信息失败: {str(e)}")
        return "获取区块信息失败"

def verify_police_record(police_no, pdf_hash=None):
    """验证警情记录的有效性和完整性"""
    try:
        # 调用合约管理器验证函数
        verification_result = cm.verify_police_record(police_no, pdf_hash)
        
        # 打印验证结果以便调试
        print(f"合约验证结果: {verification_result}")
        
        # 如果返回的是字典，直接返回结果
        if isinstance(verification_result, dict):
            return verification_result
        
        # 如果返回的是元组（旧版本兼容性），转换为字典
        if isinstance(verification_result, tuple) and len(verification_result) >= 3:
            exists, active, hash_match = verification_result[:3]
            # 如果未提供PDF哈希，则不考虑哈希匹配结果
            if pdf_hash is None or pdf_hash == "":
                print("注意: 未提供PDF哈希值，仅验证记录存在性")
                hash_match = True  # 如果不提供哈希，默认哈希匹配为真
            
            result = {
                'exists': exists,
                'active': active,
                'hash_match': hash_match,
                'verified': exists and active and hash_match
            }
            return result
            
        # 默认情况，返回验证失败
        return {
            'exists': False,
            'active': False,
            'hash_match': False,
            'verified': False,
            'error': '验证返回结果格式错误'
        }
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

def revoke_police_record(police_no, reason):
    """撤销警情记录"""
    try:
        result = cm.revoke_police_record(police_no, reason)
        
        # 记录审计日志
        cm.record_audit_action("RecordRevocation", f"撤销警情记录: {police_no}, 原因: {reason}")
        
        return {
            'success': result['success'],
            'block_number': result['block_number'],
            'tx_hash': result['tx_hash']
        }
    except Exception as e:
        print(f"撤销警情记录失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_record_count():
    """获取警情记录总数"""
    try:
        count = cm.contract_manager.call_contract_function('PoliceRecordContract', 'getRecordCount')
        return count
    except Exception as e:
        print(f"获取记录总数失败: {str(e)}")
        return 0

def blocks_list():
    """显示当前区块链中所有区块的Hash和区块总数"""
    count = 0
    block_num = w3.eth.get_block('latest').number  # 获取最新的区块号
    for i in range(block_num):
        try:
            blockn = w3.eth.get_block(i)  # 获取指定区块的信息
            print("Block", str(i), " hash:", bytes_to_hex_string(blockn.hash))
            count += 1
        except:
            print('当前区块链中没有更多区块.')
            break
    print('\n当前区块链共有 {0} 个区块.\n'.format(count))

def get_police_record(police_no):
    """获取区块链上的警情记录详细信息"""
    try:
        print(f"\n==================================================")
        print(f"获取警情编号 {police_no} 的区块链记录...")
        
        # 直接调用合约获取记录
        contract = cm.contract_manager.get_contract('PoliceRecordContract')
        
        # 首先检查记录是否存在
        try:
            exists, is_active = contract.functions.getRecordStatus(police_no).call()
            if not exists:
                print(f"警情记录 {police_no} 不存在于区块链中")
                return None
            
            # 获取基本信息
            basic_info = contract.functions.getRecordBasic(police_no).call()
            receive_time, officer, result, gps_location, is_active = basic_info
            
            # 获取哈希信息
            hash_info = contract.functions.getRecordHashes(police_no).call()
            pdf_hash, merkle_hash, ipfs_hash, timestamp = hash_info
            
            record = {
                'policeNo': police_no,
                'receiveTime': receive_time,
                'policeOfficer': officer,
                'result': result,
                'gpsLocation': gps_location,
                'pdfHash': pdf_hash,
                'merkleHash': merkle_hash,
                'ipfsHash': ipfs_hash,
                'timestamp': timestamp,
                'isActive': is_active,
                'block_number': hash_info[3]  # 使用timestamp作为区块号
            }
            
            print(f"成功获取记录: {police_no}")
            return record
        except Exception as e:
            print(f"使用多函数调用方式获取记录失败: {str(e)}")
            
            # 尝试使用旧方法
            try:
                record = contract.functions.getRecord(police_no).call()
                
                result = {
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
                
                print(f"使用旧方法成功获取记录: {police_no}")
                return result
            except Exception as e2:
                print(f"使用旧函数获取警情记录也失败: {str(e2)}")
                return None
    except Exception as e:
        print(f"获取警情记录失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def update_pdf_hash(police_no, new_pdf_hash):
    """更新警情记录的PDF哈希值
    
    Args:
        police_no: 警情编号
        new_pdf_hash: 新的PDF哈希值
        
    Returns:
        更新结果
    """
    try:
        print(f"尝试更新警情编号 {police_no} 的PDF哈希...")
        
        # 先检查记录是否存在
        verify_result = verify_police_record(police_no, "")
        if not verify_result.get('exists'):
            print(f"警情记录 {police_no} 不存在于区块链中")
            return {
                'success': False,
                'message': f"警情记录 {police_no} 不存在"
            }
        
        # 尝试调用合约更新函数
        try:
            # 检查合约是否有更新哈希的函数
            contract = cm.get_contract('PoliceRecordContract')
            if hasattr(contract.functions, 'updatePdfHash'):
                result = cm.send_contract_transaction(
                    'PoliceRecordContract',
                    'updatePdfHash',
                    police_no,
                    new_pdf_hash
                )
                
                # 记录审计操作
                cm.record_audit_action("HashUpdate", f"更新警情记录 {police_no} 的PDF哈希")
                
                print(f"PDF哈希更新成功: {new_pdf_hash}")
                return {
                    'success': True,
                    'message': "PDF哈希更新成功",
                    'tx_hash': result.get('tx_hash'),
                    'block_number': result.get('block_number')
                }
            else:
                print("合约不支持更新PDF哈希功能")
                return {
                    'success': False,
                    'message': "合约不支持更新PDF哈希功能"
                }
        except Exception as e:
            print(f"更新PDF哈希失败: {str(e)}")
            return {
                'success': False,
                'message': f"更新PDF哈希失败: {str(e)}"
            }
    except Exception as e:
        print(f"更新PDF哈希过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f"更新过程出错: {str(e)}"
        }

# 确保合约已初始化
initialize_contracts()

# 定义一个16进制字符串格式化输出函数
def bytes_to_hex_string(bs):
    return ''.join(['%02x' % b for b in bs]) 