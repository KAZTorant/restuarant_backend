const CUSTOM_PATHS = {
  'orders/statistics': '/panel/statistics/',
  'orders/summary': '/panel/summary/',
  'orders/withdrawnlist': '/panel/withdrawn-list/',
  'payments/paymentcalculation': '/panel/payment-calculation/',
  'tables/table': '/panel/tables/',
};

const AdminLayout = {
  async init() {
    const navEl = document.getElementById('sidebar-nav');
    if (!navEl) return;

    try {
      const data = await AdminAPI.navigation();
      this.renderNav(navEl, data.apps);
      this.renderUser(data.user);
    } catch (e) {
      if (e.status === 403 || e.status === 401) {
        window.location.href = '/panel/login/';
      }
    }

    this.highlightActive();
  },

  renderUser(user) {
    const nameEl = document.getElementById('topbar-user');
    const restEl = document.getElementById('topbar-restaurant');
    if (nameEl) nameEl.textContent = user.full_name || user.username;
    if (restEl && user.restaurant) restEl.textContent = user.restaurant.name;
  },

  renderNav(container, apps) {
    container.innerHTML = apps.map((app) => `
      <div class="nav-section">
        <div class="nav-app-title">${AdminUI.escapeHtml(app.name)}</div>
        ${app.models.map((m) => {
          const key = `${m.app_label}/${m.model_name}`;
          const href = CUSTOM_PATHS[key] || `/panel/models/${m.app_label}/${m.model_name}/`;
          return `<a href="${href}" class="nav-link" data-path="${href}">${AdminUI.escapeHtml(m.name)}</a>`;
        }).join('')}
      </div>`).join('');
  },

  highlightActive() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach((link) => {
      const href = link.getAttribute('href');
      if (path === href || (href !== '/panel/' && path.startsWith(href))) {
        link.classList.add('active');
      }
    });
    if (path === '/panel/' || path === '/panel') {
      document.querySelector('.nav-link[href="/panel/"]')?.classList.add('active');
    }
  },
};

document.addEventListener('DOMContentLoaded', () => AdminLayout.init());

window.AdminLayout = AdminLayout;
