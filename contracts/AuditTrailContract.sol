// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title AuditTrailContract
 * @dev 用于记录系统操作的审计跟踪智能合约
 */
contract AuditTrailContract {
    // 系统管理员
    address public admin;
    
    // 授权执行操作的地址
    mapping(address => bool) public authorizedUsers;
    
    // 审计记录结构体
    struct AuditRecord {
        uint256 id;          // 记录ID
        address user;        // 操作用户
        string action;       // 操作类型
        string details;      // 操作详情
        uint256 timestamp;   // 操作时间戳
    }
    
    // 所有审计记录
    AuditRecord[] public auditTrail;
    
    // 记录总数计数器
    uint256 public recordCount;
    
    // 事件定义
    event ActionRecorded(uint256 id, address user, string action, uint256 timestamp);
    event UserAuthorized(address user, uint256 timestamp);
    event UserDeauthorized(address user, uint256 timestamp);
    
    // 仅限管理员修饰器
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this function");
        _;
    }
    
    // 仅限授权用户修饰器
    modifier onlyAuthorized() {
        require(msg.sender == admin || authorizedUsers[msg.sender], "Caller is not authorized");
        _;
    }
    
    // 构造函数
    constructor() {
        admin = msg.sender;
        authorizedUsers[msg.sender] = true; // 管理员自动授权
        recordCount = 0;
    }
    
    /**
     * @dev 记录一个操作
     * @param action 操作类型
     * @param details 操作详情
     * @return newId 记录ID
     */
    function recordAction(string memory action, string memory details) public onlyAuthorized returns (uint256) {
        uint256 newId = recordCount++;
        
        AuditRecord memory record = AuditRecord({
            id: newId,
            user: msg.sender,
            action: action,
            details: details,
            timestamp: block.timestamp
        });
        
        auditTrail.push(record);
        
        emit ActionRecorded(newId, msg.sender, action, block.timestamp);
        
        return newId;
    }
    
    /**
     * @dev 获取审计记录总数
     * @return count 记录总数
     */
    function getAuditTrailCount() public view returns (uint256) {
        return auditTrail.length;
    }
    
    /**
     * @dev 获取指定ID的审计记录
     * @param id 记录ID
     * @return user 操作用户地址
     * @return action 操作类型
     * @return details 操作详情
     * @return timestamp 操作时间戳
     */
    function getAuditRecord(uint256 id) public view returns (
        address,
        string memory,
        string memory,
        uint256
    ) {
        require(id < auditTrail.length, "Record does not exist");
        
        AuditRecord memory record = auditTrail[id];
        return (
            record.user,
            record.action,
            record.details,
            record.timestamp
        );
    }
    
    /**
     * @dev 获取最近的n条审计记录
     * @param n 要获取的记录数量
     * @return recentIds 最近记录的ID数组
     */
    function getRecentRecords(uint256 n) public view returns (uint256[] memory) {
        uint256 count = auditTrail.length;
        
        // 如果请求的数量大于实际记录数，则调整
        if (n > count) {
            n = count;
        }
        
        uint256[] memory recentIds = new uint256[](n);
        
        // 从最新的记录开始添加
        for (uint256 i = 0; i < n; i++) {
            recentIds[i] = count - i - 1;
        }
        
        return recentIds;
    }
    
    /**
     * @dev 授权用户
     * @param user 用户地址
     */
    function authorizeUser(address user) public onlyAdmin {
        require(user != address(0), "Invalid address");
        require(!authorizedUsers[user], "User already authorized");
        
        authorizedUsers[user] = true;
        emit UserAuthorized(user, block.timestamp);
    }
    
    /**
     * @dev 撤销用户授权
     * @param user 用户地址
     */
    function deauthorizeUser(address user) public onlyAdmin {
        require(user != admin, "Cannot deauthorize admin");
        require(authorizedUsers[user], "User not authorized");
        
        authorizedUsers[user] = false;
        emit UserDeauthorized(user, block.timestamp);
    }

    /**
     * @dev 获取审计记录
     * @param recordId 记录ID
     * @return operator 操作者地址
     * @return operationType 操作类型
     * @return details 详细信息
     * @return timestamp 时间戳
     */
    function getAuditTrail(uint256 recordId) public view returns (
        address operator,
        string memory operationType,
        string memory details,
        uint256 timestamp
    ) {
        require(recordId < auditTrail.length, "Record does not exist");
        AuditRecord memory record = auditTrail[recordId];
        return (
            record.user,
            record.action,
            record.details,
            record.timestamp
        );
    }
} 