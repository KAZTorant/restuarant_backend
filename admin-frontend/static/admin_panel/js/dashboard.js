document.addEventListener('DOMContentLoaded', async () => {
  const grid = document.getElementById('modules-grid');
  if (!grid) return;
  try {
    const data = await AdminAPI.navigation();
    const welcome = document.getElementById('welcome-text');
    if (welcome) welcome.textContent = `Xoş gəldiniz${data.user.full_name ? `, ${data.user.full_name}` : ''}!`;
    grid.innerHTML = data.apps.map((app) => `
      <div class="module-card">
        <h3>${AdminUI.escapeHtml(app.name)}</h3>
        <ul>${app.models.map((m) => `<li><a href="/panel/models/${m.app_label}/${m.model_name}/">${AdminUI.escapeHtml(m.name)}</a></li>`).join('')}</ul>
      </div>`).join('');
  } catch (e) {
    AdminUI.handleApiError(e, 'Səhifə yüklənə bilmədi');
  }
});
