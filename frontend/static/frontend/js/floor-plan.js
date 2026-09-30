(function () {
  const app = document.getElementById('floor-plan-app');
  if (!app) return;

  const hallId = parseInt(app.dataset.hallId, 10);
  const pin = app.dataset.pin;
  const role = app.dataset.role;
  const fullName = app.dataset.fullName;
  const restaurantSlug = app.dataset.restaurantSlug || '';
  const isWaitress = role === 'waitress' || role === 'captain_waitress';
  const isAdmin = role === 'admin' || role === 'restaurant';

  KazzaAPI.init(pin, restaurantSlug);

  let currentHallId = hallId;
  let pollInterval = null;
  let halls = [];
  let loadSeq = 0;
  let renderedSnapshot = '';

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

  function tableSnapshot(tables) {
    return (tables || []).map((table) => [
      table.id,
      table.number,
      getTableState(table),
      table.waitress?.name || '',
      table.total_price || '',
    ].join('\u001f')).join('\u001e');
  }

  function syncText(parent, selector, className, text) {
    let node = parent.querySelector(selector);
    if (!text) {
      if (node) node.remove();
      return;
    }
    if (!node) {
      node = document.createElement('div');
      node.className = className;
      parent.appendChild(node);
    }
    if (node.textContent !== text) node.textContent = text;
  }

  function paintCard(el, table) {
    const state = getTableState(table);
    el.classList.remove('table-card--empty', 'table-card--active', 'table-card--printed', 'table-card--locked');
    el.classList.add(`table-card--${state}`);
    el.dataset.tableId = table.id;

    const badge = el.querySelector('.table-badge');
    const badgeText = getBadge(state);
    if (badge && badge.textContent !== badgeText) badge.textContent = badgeText;

    const number = el.querySelector('.table-number');
    const numberText = String(table.number);
    if (number && number.textContent !== numberText) number.textContent = numberText;

    syncText(el, '.table-meta', 'table-meta', table.waitress?.name || '');
    syncText(el, '.table-price', 'table-price', table.total_price ? `₼ ${table.total_price}` : '');
  }

  function renderTables(tables, animate) {
    const grid = document.getElementById('tables-grid');
    const snapshot = tableSnapshot(tables);

    if (!animate && snapshot === renderedSnapshot) return;

    if (!tables || tables.length === 0) {
      renderedSnapshot = snapshot;
      grid.classList.remove('tables-grid--quiet');
      grid.innerHTML = KazzaUI.emptyState('🪑', 'Bu zalda masa yoxdur', 'Zallar arasında keçid edin');
      return;
    }

    const existing = [...grid.querySelectorAll('.table-card')];
    const sameLayout = !animate
      && existing.length === tables.length
      && existing.every((el, i) => el.dataset.tableId === String(tables[i].id));

    if (sameLayout) {
      const previous = renderedSnapshot.split('\u001e');
      const next = snapshot.split('\u001e');
      tables.forEach((table, i) => {
        if (previous[i] !== next[i]) paintCard(existing[i], table);
      });
      renderedSnapshot = snapshot;
      return;
    }

    grid.classList.toggle('tables-grid--quiet', !animate);
    grid.innerHTML = tables.map((table, i) => {
      const state = getTableState(table);
      const delay = animate ? ` style="animation-delay: ${i * 0.04}s"` : '';
      return `
        <div class="table-card table-card--${state}"
             data-table-id="${table.id}"${delay}>
          <span class="table-badge">${getBadge(state)}</span>
          <div class="table-number">${table.number}</div>
          ${table.waitress?.name ? `<div class="table-meta">${table.waitress.name}</div>` : ''}
          ${table.total_price ? `<div class="table-price">₼ ${table.total_price}</div>` : ''}
        </div>`;
    }).join('');
    renderedSnapshot = snapshot;
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
        history.replaceState(null, '', `/r/${restaurantSlug}/hall/${currentHallId}/`);
        renderedSnapshot = '';
        loadTables({ silent: true, animate: true });
        renderHalls();
      });
    });
  }

  async function loadTables({ silent = false, animate = true } = {}) {
    const seq = ++loadSeq;
    const requestedHall = currentHallId;

    const grid = document.getElementById('tables-grid');
    if (!silent) {
      renderedSnapshot = '';
      grid.classList.remove('tables-grid--quiet');
      grid.innerHTML = KazzaUI.skeletonCards(8, 'table');
    }

    try {
      const tables = await KazzaAPI.fetchTablesByHallId(requestedHall);
      if (seq !== loadSeq || requestedHall !== currentHallId) return;
      renderTables(tables, animate);
    } catch (e) {
      if (seq !== loadSeq || requestedHall !== currentHallId) return;
      if (!silent) {
        grid.innerHTML = KazzaUI.emptyState('⚠️', 'Masalar yüklənə bilmədi', 'Yenidən cəhd edin');
        KazzaUI.error(KazzaUI.parseError(e, 'Masalar yüklənərkən xəta baş verdi.'));
      }
    }
  }

  async function init() {
    KazzaUI.showLoading('Zallar yüklənir...');
    try {
      halls = await KazzaAPI.fetchRooms();
      renderHalls();
      await loadTables();

      if (isAdmin) {
        pollInterval = setInterval(() => loadTables({ silent: true, animate: false }), 5000);
      }
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Səhifə yüklənərkən xəta baş verdi.'));
    } finally {
      KazzaUI.hideLoading();
    }
  }

  document.getElementById('tables-grid').addEventListener('click', (event) => {
    const card = event.target.closest('.table-card');
    if (!card || card.classList.contains('table-card--locked')) return;
    KazzaUI.showLoading('Sifariş açılır...');
    window.location.href = `/r/${restaurantSlug}/hall/${currentHallId}/table/${card.dataset.tableId}/`;
  });

  window.addEventListener('beforeunload', () => {
    if (pollInterval) clearInterval(pollInterval);
  });

  init();
})();
