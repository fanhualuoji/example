// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title PoliceRecordContract
 * @dev 用于警情记录上链存储和验证的智能合约
 */
contract PoliceRecordContract {
    // 合约拥有者（通常为警察局或管理员）
    address public owner;
    
    // 警情记录结构体
    struct PoliceRecord {
        string policeNo;         // 警情编号
        string receiveTime;      // 接警时间
        string policeOfficer;    // 出警人
        string result;           // 处置结果
        string gpsLocation;      // GPS位置
        string pdfHash;          // PDF文件哈希
        string merkleHash;       // 默克尔树根哈希
        string ipfsHash;         // IPFS哈希值
        uint256 timestamp;       // 上链时间戳
        bool isActive;           // 是否有效（未撤销）
    }
    
    // 授权地址映射
    mapping(address => bool) public authorizedUsers;
    
    // 根据警情编号存储记录
    mapping(string => PoliceRecord) public records;
    
    // 记录撤销状态
    mapping(string => bool) public revokedRecords;
    
    // 所有记录的ID数组，用于遍历
    string[] public recordIds;
    
    // 事件定义
    event RecordAdded(string policeNo, string ipfsHash, uint256 timestamp);
    event RecordRevoked(string policeNo, uint256 timestamp, string reason);
    event UserAuthorized(address user, uint256 timestamp);
    event UserDeauthorized(address user, uint256 timestamp);
    
    // 仅合约拥有者可执行的修饰器
    modifier onlyOwner() {
        require(msg.sender == owner, "Only the contract owner can call this function");
        _;
    }
    
    // 仅授权用户可执行的修饰器
    modifier onlyAuthorized() {
        require(msg.sender == owner || authorizedUsers[msg.sender], "Caller is not authorized");
        _;
    }
    
    // 构造函数，设置合约拥有者为部署者
    constructor() {
        owner = msg.sender;
        authorizedUsers[msg.sender] = true; // 合约创建者自动授权
    }
    
    /**
     * @dev 添加新的警情记录
     * @param policeNo 警情编号
     * @param receiveTime 接警时间
     * @param policeOfficer 出警人
     * @param result 处置结果
     * @param gpsLocation GPS位置
     * @param pdfHash PDF哈希值
     * @param merkleHash 默克尔树根哈希
     * @param ipfsHash IPFS哈希
     */
    function addRecord(
        string memory policeNo,
        string memory receiveTime,
        string memory policeOfficer,
        string memory result,
        string memory gpsLocation,
        string memory pdfHash,
        string memory merkleHash,
        string memory ipfsHash
    ) public onlyAuthorized {
        // 检查记录是否已存在
        require(bytes(records[policeNo].policeNo).length == 0, "Record already exists");
        
        // 创建新记录
        records[policeNo] = PoliceRecord({
            policeNo: policeNo,
            receiveTime: receiveTime,
            policeOfficer: policeOfficer,
            result: result,
            gpsLocation: gpsLocation,
            pdfHash: pdfHash,
            merkleHash: merkleHash,
            ipfsHash: ipfsHash,
            timestamp: block.timestamp,
            isActive: true
        });
        
        // 添加到记录ID数组中
        recordIds.push(policeNo);
        
        // 触发事件
        emit RecordAdded(policeNo, ipfsHash, block.timestamp);
    }
    
    /**
     * @dev 撤销警情记录
     * @param policeNo 要撤销的警情编号
     * @param reason 撤销原因
     */
    function revokeRecord(string memory policeNo, string memory reason) public onlyAuthorized {
        // 检查记录是否存在且未被撤销
        require(bytes(records[policeNo].policeNo).length > 0, "Record does not exist");
        require(!revokedRecords[policeNo], "Record already revoked");
        
        // 标记为已撤销
        revokedRecords[policeNo] = true;
        
        // 触发撤销事件
        emit RecordRevoked(policeNo, block.timestamp, reason);
    }
    
    /**
     * @dev 验证记录的有效性和完整性
     * @param policeNo 警情编号
     * @param pdfHash PDF哈希值（用于验证）
     * @return exists 记录是否存在
     * @return active 记录是否未被撤销
     * @return hashMatch PDF哈希是否匹配
     */
    function verifyRecord(string memory policeNo, string memory pdfHash) public view returns (bool exists, bool active, bool hashMatch) {
        // 检查记录是否存在
        exists = bytes(records[policeNo].policeNo).length > 0;
        
        // 如果记录存在，检查其它条件
        if (exists) {
            active = !revokedRecords[policeNo];
            hashMatch = keccak256(abi.encodePacked(records[policeNo].pdfHash)) == keccak256(abi.encodePacked(pdfHash));
        } else {
            active = false;
            hashMatch = false;
        }
    }
    
    /**
     * @dev 获取警情记录基本信息
     * @param policeNo 警情编号
     * @return receiveTime 接警时间
     * @return policeOfficer 出警人
     * @return result 处置结果
     * @return gpsLocation GPS位置
     * @return isActive 记录是否有效（未撤销）
     */
    function getRecordBasic(string memory policeNo) public view returns (
        string memory receiveTime,
        string memory policeOfficer,
        string memory result,
        string memory gpsLocation,
        bool isActive
    ) {
        require(bytes(records[policeNo].policeNo).length > 0, "Record does not exist");
        
        PoliceRecord memory record = records[policeNo];
        return (
            record.receiveTime,
            record.policeOfficer,
            record.result,
            record.gpsLocation,
            !revokedRecords[policeNo]
        );
    }
    
    /**
     * @dev 获取警情记录哈希信息
     * @param policeNo 警情编号
     * @return pdfHash PDF哈希
     * @return merkleHash 默克尔树根哈希
     * @return ipfsHash IPFS哈希值
     * @return timestamp 上链时间戳
     */
    function getRecordHashes(string memory policeNo) public view returns (
        string memory pdfHash,
        string memory merkleHash,
        string memory ipfsHash,
        uint256 timestamp
    ) {
        require(bytes(records[policeNo].policeNo).length > 0, "Record does not exist");
        
        PoliceRecord memory record = records[policeNo];
        return (
            record.pdfHash,
            record.merkleHash,
            record.ipfsHash,
            record.timestamp
        );
    }
    
    /**
     * @dev 获取警情记录是否有效
     * @param policeNo 警情编号
     * @return exists 记录是否存在
     * @return isActive 记录是否有效（未撤销）
     */
    function getRecordStatus(string memory policeNo) public view returns (
        bool exists,
        bool isActive
    ) {
        exists = bytes(records[policeNo].policeNo).length > 0;
        isActive = exists && !revokedRecords[policeNo];
        return (exists, isActive);
    }
    
    /**
     * @dev 获取警情记录详情（旧版，已废弃，请使用getRecordBasic和getRecordHashes代替）
     * @param policeNo 警情编号
     * @return 警情记录的所有字段
     */
    function getRecord(string memory policeNo) public view returns (
        string memory,
        string memory,
        string memory,
        string memory,
        string memory,
        string memory,
        string memory,
        uint256,
        bool
    ) {
        require(bytes(records[policeNo].policeNo).length > 0, "Record does not exist");
        
        PoliceRecord memory record = records[policeNo];
        return (
            record.receiveTime,
            record.policeOfficer,
            record.result,
            record.gpsLocation,
            record.pdfHash,
            record.merkleHash,
            record.ipfsHash,
            record.timestamp,
            !revokedRecords[policeNo]
        );
    }
    
    /**
     * @dev 获取记录总数
     * @return count 记录总数
     */
    function getRecordCount() public view returns (uint256) {
        return recordIds.length;
    }
    
    /**
     * @dev 授权新用户
     * @param user 要授权的用户地址
     */
    function authorizeUser(address user) public onlyOwner {
        require(user != address(0), "Invalid address");
        require(!authorizedUsers[user], "User already authorized");
        
        authorizedUsers[user] = true;
        emit UserAuthorized(user, block.timestamp);
    }
    
    /**
     * @dev 撤销用户授权
     * @param user 要撤销授权的用户地址
     */
    function deauthorizeUser(address user) public onlyOwner {
        require(user != owner, "Cannot deauthorize owner");
        require(authorizedUsers[user], "User not authorized");
        
        authorizedUsers[user] = false;
        emit UserDeauthorized(user, block.timestamp);
    }
    
    /**
     * @dev 获取警情记录ID（按索引）
     * @param index 索引值
     * @return policeNo 警情编号
     */
    function getRecordIdAtIndex(uint256 index) public view returns (string memory) {
        require(index < recordIds.length, "Index out of bounds");
        return recordIds[index];
    }
} 