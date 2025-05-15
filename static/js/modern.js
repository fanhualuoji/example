// 智警链存系统 - 现代JavaScript文件

// DOM完全加载后执行
document.addEventListener('DOMContentLoaded', function () {
  // ===== 页面加载动画 =====
  const pageLoader = document.getElementById('page-loader');
  if (pageLoader) {
    // 在页面加载完成后延迟隐藏加载动画
    setTimeout(function () {
      pageLoader.classList.add('hidden');
      // 动画完成后移除元素
      setTimeout(function () {
        pageLoader.remove();
      }, 500);
    }, 800);
  }

  // ===== 主题切换功能 =====
  const themeToggleBtn = document.getElementById('theme-toggle');

  // 检查本地存储中的主题偏好
  const savedTheme = localStorage.getItem('theme');

  // 如果有保存的主题设置，应用它
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
  } else {
    // 如果没有保存的设置，检查系统偏好
    const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = prefersDarkMode ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', initialTheme);
    localStorage.setItem('theme', initialTheme);
  }

  // 主题切换按钮点击事件
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', function () {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';

      // 更改主题
      document.documentElement.setAttribute('data-theme', newTheme);

      // 保存到本地存储
      localStorage.setItem('theme', newTheme);

      // 按钮动画效果
      this.classList.add('animate__animated', 'animate__rubberBand');
      setTimeout(() => {
        this.classList.remove('animate__animated', 'animate__rubberBand');
      }, 750);
    });
  }

  // ===== 侧边栏折叠功能 =====
  const sidebarToggleBtn = document.getElementById('sidebar-toggle');

  // 检查本地存储中的侧边栏状态
  const sidebarState = localStorage.getItem('sidebar-collapsed');

  if (sidebarState === 'true') {
    document.body.classList.add('sidebar-collapsed');
  }

  // 侧边栏切换按钮点击事件
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', function () {
      // 在移动设备上切换侧边栏显示
      if (window.innerWidth < 992) {
        document.body.classList.toggle('sidebar-open');
        return;
      }

      // 在桌面设备上折叠/展开侧边栏
      document.body.classList.toggle('sidebar-collapsed');

      // 保存状态到本地存储
      const isCollapsed = document.body.classList.contains('sidebar-collapsed');
      localStorage.setItem('sidebar-collapsed', isCollapsed);
    });
  }

  // ===== 用户下拉菜单 =====
  const userMenuToggle = document.querySelector('.user-menu-toggle');

  if (userMenuToggle) {
    userMenuToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      const userMenu = this.closest('.user-menu');
      userMenu.classList.toggle('active');
    });

    // 点击外部区域关闭下拉菜单
    document.addEventListener('click', function (e) {
      const userMenu = document.querySelector('.user-menu');
      if (userMenu && !userMenu.contains(e.target)) {
        userMenu.classList.remove('active');
      }
    });
  }

  // ===== 警告框关闭 =====
  const alertCloseButtons = document.querySelectorAll('.alert-close');

  alertCloseButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      const alert = this.closest('.alert');

      // 添加淡出动画
      alert.classList.add('animate__fadeOut');

      // 动画结束后移除元素
      setTimeout(function () {
        alert.remove();
      }, 500);
    });
  });

  // 自动隐藏警告框
  setTimeout(function () {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function (alert, index) {
      // 逐个淡出警告框，错开时间
      setTimeout(function () {
        alert.classList.add('animate__fadeOut');
        setTimeout(function () {
          alert.remove();
        }, 500);
      }, index * 200);
    });
  }, 5000);

  // ===== 响应式处理 =====
  // 监听窗口大小变化
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 992 && document.body.classList.contains('sidebar-open')) {
      document.body.classList.remove('sidebar-open');
    }
  });

  // ===== 增强表单元素 =====
  // 格式化日期时间输入
  const dateElements = document.querySelectorAll('.date-format');
  dateElements.forEach(function (element) {
    const dateStr = element.textContent;
    if (dateStr && dateStr.trim()) {
      try {
        const date = new Date(dateStr);
        if (!isNaN(date)) {
          element.textContent = date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          });
        }
      } catch (e) {
        console.error('日期格式化错误:', e);
      }
    }
  });

  // ===== 动画效果 =====
  // 为卡片添加交错渐入效果
  const cards = document.querySelectorAll('.card');
  cards.forEach(function (card, index) {
    card.classList.add('animate__animated', 'animate__fadeInUp');
    card.style.animationDelay = (index * 0.1) + 's';
  });

  // ===== 复制到剪贴板功能 =====
  const copyButtons = document.querySelectorAll('.btn-copy');
  copyButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      const textToCopy = this.getAttribute('data-copy');
      if (!textToCopy) return;

      // 创建临时输入框
      const tempInput = document.createElement('input');
      tempInput.value = textToCopy;
      document.body.appendChild(tempInput);
      tempInput.select();

      try {
        // 执行复制命令
        const success = document.execCommand('copy');
        if (success) {
          // 显示成功动画
          const originalContent = this.innerHTML;
          const originalWidth = this.offsetWidth;
          this.style.minWidth = originalWidth + 'px';
          this.innerHTML = '<i class="fas fa-check"></i> 已复制';
          this.classList.add('animate__animated', 'animate__pulse');

          // 恢复原来的按钮文本
          setTimeout(() => {
            this.innerHTML = originalContent;
            this.classList.remove('animate__animated', 'animate__pulse');
            this.style.minWidth = '';
          }, 2000);
        }
      } catch (err) {
        console.error('复制失败: ', err);
      }

      // 移除临时输入框
      document.body.removeChild(tempInput);
    });
  });

  // ===== 检测区块链连接状态 =====
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