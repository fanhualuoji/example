import hashlib

# 用于生成各类哈希值的统一接口函数
def hash_function(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

# 用于计算电子文件哈希值的函数
def hash_certificate(certificate_file):
    try:
        with open(certificate_file, 'rb') as cert_file:
            file_content = cert_file.read()
        
        # 计算文件SHA-256哈希值
        hash_obj = hashlib.sha256(file_content)
        hex_digest = hash_obj.hexdigest()
        
        return hex_digest
    except FileNotFoundError:
        print(f"错误: 找不到文件 {certificate_file}")
        raise
    except PermissionError:
        print(f"错误: 没有权限读取文件 {certificate_file}")
        raise
    except Exception as e:
        print(f"计算文件哈希值时出错: {str(e)}")
        raise

# 生成警情数据的Merkle树，用于数据验证
def merkle_tree(dict_info):
    # 确保传入的是字典类型
    if not isinstance(dict_info, dict):
        raise ValueError("输入必须是字典类型")
    
    # 警情相关字段的哈希值列表
    hash_list = []
    
    # 计算关键字段的哈希值并加入列表
    for key, value in dict_info.items():
        # 组合键值对为"键:值"格式再计算哈希
        item_content = f"{key}:{value}"
        item_hash = hash_function(item_content)
        hash_list.append(item_hash)
    
    # 如果列表长度是奇数，则复制最后一个元素以形成偶数对
    if len(hash_list) % 2 == 1:
        hash_list.append(hash_list[-1])
    
    # 计算Merkle树每一层，直到得到根哈希
    merkle_root = get_merkle_root(hash_list)
    
    return merkle_root

# 递归计算Merkle树的根哈希
def get_merkle_root(hash_list):
    # 如果只有一个哈希值，则它就是根哈希
    if len(hash_list) == 1:
        return hash_list[0]
    
    # 构建下一层的哈希列表
    new_hash_list = []
    
    # 每次取两个哈希值，计算它们的组合哈希
    for i in range(0, len(hash_list), 2):
        # 如果到了列表末尾且只剩一个元素，则与自身组合
        if i + 1 == len(hash_list):
            combined_hash = hash_function(hash_list[i] + hash_list[i])
        else:
            combined_hash = hash_function(hash_list[i] + hash_list[i+1])
        
        new_hash_list.append(combined_hash)
    
    # 递归调用直到得到根哈希
    return get_merkle_root(new_hash_list) 