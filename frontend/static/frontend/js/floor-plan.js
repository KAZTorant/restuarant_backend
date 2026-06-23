(function () {
  const app = document.getElementById('floor-plan-app');
  if (!app) return;

  const hallId = parseInt(app.dataset.hallId, 10);
  const pin = app.dataset.pin;
  const role = app.dataset.role;
  const fullName = app.dataset.fullName;
  const isWaitress = role === 'waitress' || role === 'captain_waitress';
  const isAdmin = role === 'admin' || role === 'restaurant';

  KazzaAPI.init(pin);

  let currentHallId = hallId;
  let pollInterval = null;
  let halls = [];
  let isLoading = false;

  function getTableState(table) {
    if (isWaitress && table.waitress?.name && table.waitress.name !== fullName) {
      return 'locked';
    }
    if (table.print_check) return 'printed';
    if (table.waitress?.id === 0 || !table.waitress?.name) return 'empty';
    return 'active';
  }

  function getBadge(state) {
    const badges = {
      empty: 'Boş',
      active: 'Aktiv',
      printed: 'Çek',
      locked: 'Başqa ofsiant',
    };
    return badges[state] || '';
  }

  function renderTables(tables) {
    const grid = document.getElementById('tables-grid');

    if (!tables || tables.length === 0) {
      grid.innerHTML = KazzaUI.emptyState('🪑', 'Bu zalda masa yoxdur', 'Zallar arasında keçid edin');
      return;
    }

    grid.innerHTML = tables.map((table, i) => {
      const state = getTableState(table);
      return `
        <div class="table-card table-card--${state}"
             data-table-id="${table.id}"
             style="animation-delay: ${i * 0.04}s">
          <span class="table-badge">${getBadge(state)}</span>
          <div class="table-number">${table.number}</div>
          ${table.waitress?.name ? `<div class="table-meta">${table.waitress.name}</div>` : ''}
          ${table.total_price ? `<div class="table-price">₼ ${table.total_price}</div>` : ''}
        </div>`;
    }).join('');

    grid.querySelectorAll('.table-card:not(.table-card--locked)').forEach((el) => {
      el.addEventListener('click', () => {
        KazzaUI.showLoading('Sifariş açılır...');
        window.location.href = `/hall/${currentHallId}/table/${el.dataset.tableId}/`;
      });
    });
  }

  function renderHalls() {
    const bar = document.getElementById('halls-bar');
    const refreshHtml = isAdmin
      ? `<span class="refresh-indicator"><span class="refresh-dot"></span>Canlı</span>`
      : '';

    bar.innerHTML = halls.map((hall) => `
      <div class="hall-pill ${hall.id === currentHallId ? 'active' : ''}" data-hall-id="${hall.id}">
        <div class="hall-pill-name">${hall.name}</div>
        ${hall.description ? `<div class="hall-pill-desc">${hall.description}</div>` : ''}
      </div>
    `).join('') + refreshHtml;

    bar.querySelectorAll('.hall-pill').forEach((el) => {
      el.addEventListener('click', () => {
        currentHallId = parseInt(el.dataset.hallId, 10);
        history.replaceState(null, '', `/hall/${currentHallId}/`);
        loadTables(true);
        renderHalls();
      });
    });
  }

  async function loadTables(silent = false) {
    if (isLoading) return;
    isLoading = true;

    const grid = document.getElementById('tables-grid');
    if (!silent) {
      grid.innerHTML = KazzaUI.skeletonCards(8, 'table');
    }

    try {
      const tables = await KazzaAPI.fetchTablesByHallId(currentHallId);
      renderTables(tables);
    } catch (e) {
      grid.innerHTML = KazzaUI.emptyState('⚠️', 'Masalar yüklənə bilmədi', 'Yenidən cəhd edin');
      KazzaUI.error(KazzaUI.parseError(e, 'Masalar yüklənərkən xəta baş verdi.'));
    } finally {
      isLoading = false;
    }
  }

  async function init() {
    KazzaUI.showLoading('Zallar yüklənir...');
    try {
      halls = await KazzaAPI.fetchRooms();
      renderHalls();
      await loadTables();

      if (isAdmin) {
        pollInterval = setInterval(() => loadTables(true), 5000);
      }
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Səhifə yüklənərkən xəta baş verdi.'));
    } finally {
      KazzaUI.hideLoading();
    }
  }

  window.addEventListener('beforeunload', () => {
    if (pollInterval) clearInterval(pollInterval);
  });

  init();
})();
