document.addEventListener('DOMContentLoaded', async () => {
  const grid = document.getElementById('tables-grid');
  try {
    const data = await AdminUI.withLoading(() => AdminAPI.list('tables', 'table', { page_size: '200' }));
    const grouped = {};
    data.results.forEach((row) => {
      const room = String(row.room ?? 'Digər');
      if (!grouped[room]) grouped[room] = [];
      grouped[room].push(row);
    });
    grid.innerHTML = Object.entries(grouped).map(([room, tables]) => `
      <div class="room-card">
        <h3>${AdminUI.escapeHtml(room)}</h3>
        <div class="table-items">
          ${tables.map((t) => `
            <a href="/panel/models/tables/table/${t.id}/change/" class="table-item">
              <div class="name">${AdminUI.escapeHtml(t.name ?? t.id)}</div>
            </a>`).join('')}
        </div>
      </div>`).join('') || '<p class="empty-state">Masa tapılmadı</p>';
  } catch (e) {
    if (e.status === 401) window.location.href = '/panel/login/';
    grid.innerHTML = '<p class="empty-state">Xəta baş verdi</p>';
  }
});
