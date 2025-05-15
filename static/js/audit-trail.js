/**
 * 审计记录功能
 * 用于记录用户在前端执行的重要操作到区块链上
 */

class AuditTrailManager {
  constructor() {
    // 初始化
    this.apiEndpoint = '/api/record_audit';
  }

  /**
   * 记录一条审计操作
   * @param {string} action - 操作类型
   * @param {string} details - 操作详情
   * @returns {Promise} - 返回Promise对象
   */
  recordAction(action, details) {
    return new Promise((resolve, reject) => {
      fetch(this.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: action,
          details: details
        })
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // 减少控制台输出
            if (window.debugMode) {
              console.log(`审计记录成功: ID=${data.record_id}`);
            }
            resolve(data);
          } else {
            console.error(`审计记录失败: ${data.message}`);
            reject(new Error(data.message));
          }
        })
        .catch(error => {
          console.error('审计记录请求失败:', error);
          reject(error);
        });
    });
  }

  /**
   * 记录警情数据上链操作
   * @param {string} policeNo - 警情编号
   * @param {string} details - 其他详情
   * @returns {Promise}
   */
  recordDataUpload(policeNo, details = '') {
    return this.recordAction(
      '警情数据上链',
      `警情编号: ${policeNo}${details ? ', ' + details : ''}`
    );
  }

  /**
   * 记录警情数据验证操作
   * @param {string} policeNo - 警情编号
   * @returns {Promise}
   */
  recordDataVerify(policeNo) {
    return this.recordAction(
      '警情数据验证',
      `警情编号: ${policeNo}`
    );
  }

  /**
   * 记录警情数据撤销操作
   * @param {string} policeNo - 警情编号
   * @param {string} reason - 撤销原因
   * @returns {Promise}
   */
  recordDataRevoke(policeNo, reason) {
    return this.recordAction(
      '警情数据撤销',
      `警情编号: ${policeNo}, 撤销原因: ${reason}`
    );
  }

  /**
   * 记录系统登录操作
   * @param {string} username - 用户名
   * @returns {Promise}
   */
  recordLogin(username) {
    return this.recordAction(
      '用户登录',
      `用户: ${username}`
    );
  }

  /**
   * 记录系统登出操作
   * @param {string} username - 用户名
   * @returns {Promise}
   */
  recordLogout(username) {
    return this.recordAction(
      '用户登出',
      `用户: ${username}`
    );
  }

  /**
   * 记录警情数据查询操作
   * @param {string} policeNo - 警情编号
   * @returns {Promise}
   */
  recordDataQuery(policeNo) {
    return this.recordAction(
      '警情数据查询',
      `警情编号: ${policeNo}`
    );
  }

  /**
   * 记录自定义操作
   * @param {string} action - 操作类型
   * @param {string} details - 操作详情
   * @returns {Promise}
   */
  recordCustomAction(action, details) {
    return this.recordAction(action, details);
  }
}

// 创建全局审计管理器实例
const auditTrail = new AuditTrailManager();

// 设置调试模式 - 默认为false，可通过页面设置
window.debugMode = false;

// 在页面加载完成后，为相关按钮添加审计记录功能
document.addEventListener('DOMContentLoaded', function () {
  // 上传页面
  const uploadForm = document.querySelector('form[action*="upload"]');
  if (uploadForm) {
    uploadForm.addEventListener('submit', function (e) {
      // 记录上传操作将在后端完成，无需前端日志
    });
  }

  // 验证页面
  const verifyForm = document.querySelector('form[action*="verify"]');
  if (verifyForm) {
    verifyForm.addEventListener('submit', function (e) {
      const policeNoInput = this.querySelector('input[name="police_no"]');
      if (policeNoInput && policeNoInput.value && window.debugMode) {
        console.log(`验证警情记录: ${policeNoInput.value}`);
      }
    });
  }

  // 撤销页面
  const revokeForm = document.querySelector('form[action*="revoke"]');
  if (revokeForm) {
    revokeForm.addEventListener('submit', function (e) {
      const policeNoInput = this.querySelector('input[name="police_no"]');
      if (policeNoInput && policeNoInput.value && window.debugMode) {
        console.log(`撤销警情记录: ${policeNoInput.value}`);
      }
    });
  }

  // 查询页面
  const queryForm = document.querySelector('form[action*="query"]');
  if (queryForm) {
    queryForm.addEventListener('submit', function (e) {
      const policeNoInput = this.querySelector('input[name="police_no"]');
      if (policeNoInput && policeNoInput.value && window.debugMode) {
        console.log(`查询警情记录: ${policeNoInput.value}`);
      }
    });
  }

  // 登录页面
  const loginForm = document.querySelector('form[action*="login"]');
  if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
      const usernameInput = this.querySelector('input[name="username"]');
      if (usernameInput && usernameInput.value && window.debugMode) {
        console.log(`用户登录: ${usernameInput.value}`);
      }
    });
  }

  // 登出链接
  const logoutLink = document.querySelector('a[href*="logout"]');
  if (logoutLink) {
    logoutLink.addEventListener('click', function (e) {
      if (window.currentUser && window.debugMode) {
        console.log(`用户登出: ${window.currentUser}`);
      }
    });
  }
});

// 导出审计管理器
window.auditTrail = auditTrail; 