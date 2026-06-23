const KazzaUI = {
  _loadingCount: 0,

  showLoading(message = 'Yüklənir...') {
    this._loadingCount += 1;
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'loading-overlay';
      overlay.className = 'loading-overlay';
      overlay.innerHTML = `
        <div class="loading-card">
          <div class="loading-spinner"></div>
          <p class="loading-text">${message}</p>
        </div>`;
      document.body.appendChild(overlay);
    } else {
      overlay.querySelector('.loading-text').textContent = message;
      overlay.classList.remove('hidden');
    }
  },

  hideLoading() {
    this._loadingCount = Math.max(0, this._loadingCount - 1);
    if (this._loadingCount === 0) {
      const overlay = document.getElementById('loading-overlay');
      if (overlay) overlay.classList.add('hidden');
    }
  },

  forceHideLoading() {
    this._loadingCount = 0;
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
  },

  toast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const icons = {
      success: '✓',
      error: '✕',
      warning: '!',
      info: 'i',
    };

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <div class="toast-body">
        <p class="toast-message">${message}</p>
      </div>
      <button class="toast-close" aria-label="Bağla">×</button>`;

    const remove = () => {
      toast.classList.add('toast--exit');
      setTimeout(() => toast.remove(), 300);
    };

    toast.querySelector('.toast-close').addEventListener('click', remove);
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('toast--visible'));
    setTimeout(remove, duration);
  },

  success(msg) { this.toast(msg, 'success'); },
  error(msg) { this.toast(msg, 'error', 5000); },
  warning(msg) { this.toast(msg, 'warning'); },
  info(msg) { this.toast(msg, 'info'); },

  parseError(err, fallback = 'Xəta baş verdi. Yenidən cəhd edin.') {
    if (!err) return fallback;
    if (err.name === 'TypeError' && !navigator.onLine) {
      return 'İnternet bağlantısı yoxdur. Zəhmət olmasa yenidən cəhd edin.';
    }
    if (err.response) {
      const status = err.response.status;
      const data = err.data;
      if (status === 404) {
        if (data?.error === 'User not found') return 'Yanlış PIN daxil etdiniz. Yenidən cəhd edin.';
        return 'Axtardığınız məlumat tapılmadı.';
      }
      if (status === 400) {
        if (data?.error) return data.error;
        if (data?.pin) return 'PIN düzgün deyil.';
        return 'Daxil etdiyiniz məlumat düzgün deyil.';
      }
      if (status === 401 || status === 403) {
        return 'Giriş icazəniz yoxdur. Yenidən daxil olun.';
      }
      if (status >= 500) return 'Server xətası baş verdi. Bir az sonra yenidən cəhd edin.';
    }
    if (err.message && err.message.includes('Failed to fetch')) {
      return 'Serverə qoşulmaq mümkün olmadı. Bağlantınızı yoxlayın.';
    }
    return fallback;
  },

  skeletonCards(count = 6, type = 'table') {
    return Array.from({ length: count }, () =>
      `<div class="skeleton skeleton--${type}"></div>`
    ).join('');
  },

  emptyState(icon, title, subtitle = '') {
    return `
      <div class="empty-state">
        <div class="empty-state-icon">${icon}</div>
        <h3 class="empty-state-title">${title}</h3>
        ${subtitle ? `<p class="empty-state-sub">${subtitle}</p>` : ''}
      </div>`;
  },

  alertBox(message, type = 'error') {
    return `
      <div class="alert alert--${type}" role="alert">
        <span class="alert-icon">${type === 'error' ? '✕' : '!'}</span>
        <span>${message}</span>
      </div>`;
  },

  async withLoading(promise, message = 'Yüklənir...') {
    this.showLoading(message);
    try {
      return await promise;
    } finally {
      this.hideLoading();
    }
  },
};

window.KazzaUI = KazzaUI;
