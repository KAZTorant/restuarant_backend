const AdminUI = {
  _loading: 0,

  showLoading() {
    this._loading += 1;
    let el = document.getElementById('admin-loading');
    if (!el) {
      el = document.createElement('div');
      el.id = 'admin-loading';
      el.className = 'loading-overlay';
      el.innerHTML = '<div class="spinner"></div>';
      document.body.appendChild(el);
    }
    el.classList.remove('hidden');
  },

  hideLoading() {
    this._loading = Math.max(0, this._loading - 1);
    if (this._loading === 0) {
      const el = document.getElementById('admin-loading');
      if (el) el.classList.add('hidden');
    }
  },

  toast(message, type = 'info') {
    let c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = message;
    c.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  },

  confirm(msg) {
    return window.confirm(msg);
  },

  escapeHtml(str) {
    if (str === null || str === undefined) return '—';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  },

  formatValue(val) {
    if (val === true) return '✓';
    if (val === false) return '—';
    if (val === null || val === undefined) return '—';
    return AdminUI.escapeHtml(val);
  },

  openModal(title, bodyHtml, wide = false) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal ${wide ? 'wide' : ''}">
        <div class="modal-header">
          <h2>${AdminUI.escapeHtml(title)}</h2>
          <button class="modal-close" type="button">&times;</button>
        </div>
        <div class="modal-body">${bodyHtml}</div>
      </div>`;
    overlay.querySelector('.modal-close').onclick = () => overlay.remove();
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    document.body.appendChild(overlay);
    return overlay;
  },

  async withLoading(fn) {
    AdminUI.showLoading();
    try { return await fn(); } finally { AdminUI.hideLoading(); }
  },
};

window.AdminUI = AdminUI;
