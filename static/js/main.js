// 警情链存系统主JavaScript文件

// 文档加载完成后执行
document.addEventListener('DOMContentLoaded', function () {
  // 自动关闭提示信息
  setTimeout(function () {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function (alert) {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 5000);

  // 添加工具提示
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // 格式化日期时间元素
  const dateElements = document.querySelectorAll('.format-date');
  dateElements.forEach(function (element) {
    const dateStr = element.textContent.trim();
    if (dateStr) {
      try {
        const date = new Date(dateStr);
        element.textContent = date.toLocaleString('zh-CN');
      } catch (e) {
        console.error('日期格式化错误:', e);
      }
    }
  });

  // 复制到剪贴板功能
  const copyButtons = document.querySelectorAll('.btn-copy');
  copyButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      const textToCopy = this.getAttribute('data-copy');
      const tempInput = document.createElement('input');
      tempInput.value = textToCopy;
      document.body.appendChild(tempInput);
      tempInput.select();
      document.execCommand('copy');
      document.body.removeChild(tempInput);

      // 显示复制成功提示
      const originalText = this.innerHTML;
      this.innerHTML = '<i class="fas fa-check"></i> 已复制';
      setTimeout(function () {
        button.innerHTML = originalText;
      }, 2000);
    });
  });

  // 检测浏览器是否支持区块链连接
  const blockchainStatusElem = document.getElementById('blockchain-status');
  if (blockchainStatusElem) {
    fetch('/check_blockchain')
      .then(response => response.json())
      .then(data => {
        if (data.connected) {
          blockchainStatusElem.innerHTML = '<i class="fas fa-check-circle text-success"></i> 区块链已连接';
          blockchainStatusElem.classList.add('text-success');
        } else {
          blockchainStatusElem.innerHTML = '<i class="fas fa-times-circle text-danger"></i> 区块链未连接';
          blockchainStatusElem.classList.add('text-danger');
        }
      })
      .catch(error => {
        console.error('区块链状态检查出错:', error);
        blockchainStatusElem.innerHTML = '<i class="fas fa-exclamation-circle text-warning"></i> 区块链状态未知';
        blockchainStatusElem.classList.add('text-warning');
      });
  }
}); 