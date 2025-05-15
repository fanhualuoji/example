import os
import json
import subprocess
import tempfile

def compile_contract_with_viaIR(contract_path, output_dir=None):
    """使用--via-ir选项编译合约"""
    if not os.path.exists(contract_path):
        raise FileNotFoundError(f"合约文件不存在: {contract_path}")
    
    # 获取合约名称
    contract_name = os.path.basename(contract_path).replace('.sol', '')
    
    # 如果没有指定输出目录，使用合约所在目录
    if output_dir is None:
        output_dir = os.path.dirname(contract_path)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 输出文件路径
    abi_path = os.path.join(output_dir, f"{contract_name}.abi")
    bin_path = os.path.join(output_dir, f"{contract_name}.bin")
    
    # solc命令
    solc_path = os.path.join(os.path.expanduser('~'), '.solcx', 'solc-v0.8.17', 'solc.exe')
    
    if not os.path.exists(solc_path):
        # 如果找不到预期路径的solc，尝试查找系统中的solc
        try:
            solc_path = 'solc'  # 假设solc在PATH中
        except:
            raise FileNotFoundError("找不到solc编译器。请确保已安装solc或py-solc-x。")
    
    print(f"使用solc编译器: {solc_path}")
    print(f"编译合约: {contract_path}")
    print(f"使用--via-ir选项")
    
    # 编译命令
    cmd = [
        solc_path,
        '--optimize',
        '--optimize-runs', '200',
        '--via-ir',
        '--abi', '--bin',
        '--overwrite',
        '-o', output_dir,
        contract_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("编译成功!")
        print(f"输出文件: {abi_path}, {bin_path}")
        
        # 读取ABI和二进制
        with open(abi_path, 'r') as f:
            abi = json.load(f)
        
        with open(bin_path, 'r') as f:
            bin_code = f.read().strip()
        
        return {
            'abi': abi,
            'bin': bin_code,
            'contract_name': contract_name
        }
    
    except subprocess.CalledProcessError as e:
        print(f"编译失败: {e}")
        print(f"命令: {' '.join(cmd)}")
        print(f"标准输出: {e.stdout}")
        print(f"错误输出: {e.stderr}")
        raise
    except Exception as e:
        print(f"发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    # 编译所有合约
    contracts_dir = 'contracts'
    
    # 确保contracts目录存在
    if not os.path.exists(contracts_dir):
        os.makedirs(contracts_dir)
    
    # 编译PoliceRecordContract.sol
    police_contract_path = os.path.join(contracts_dir, 'PoliceRecordContract.sol')
    if os.path.exists(police_contract_path):
        compile_contract_with_viaIR(police_contract_path)
    else:
        print(f"警告: {police_contract_path} 不存在")
    
    # 编译AuditTrailContract.sol
    audit_contract_path = os.path.join(contracts_dir, 'AuditTrailContract.sol')
    if os.path.exists(audit_contract_path):
        compile_contract_with_viaIR(audit_contract_path)
    else:
        print(f"警告: {audit_contract_path} 不存在") 