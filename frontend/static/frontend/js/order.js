(function () {
  const app = document.getElementById('order-app');
  if (!app) return;

  const hallId = parseInt(app.dataset.hallId, 10);
  const tableId = parseInt(app.dataset.tableId, 10);
  const pin = app.dataset.pin;
  const role = app.dataset.role;
  const restaurantSlug = app.dataset.restaurantSlug || '';

  KazzaAPI.init(pin, restaurantSlug);

  async function refreshTableDetails() {
    try {
      const details = await KazzaAPI.fetchTableDetails(tableId);
      document.getElementById('table-number').textContent = details.number;
      document.getElementById('total-price').textContent = `₼ ${details.total_price.toFixed(2)}`;
      ActionsPanel.setTotalPrice(details.total_price);
      ActionsPanel.setPrintCheck(details.print_check);
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Masa məlumatları yenilənə bilmədi.'));
    }
  }

  EventBus.on('orderItemAdded', refreshTableDetails);

  KazzaUI.showLoading('Sifariş yüklənir...');

  Promise.all([
    OrderItems.init(tableId, role),
    MenuPanel.init(tableId),
    refreshTableDetails(),
  ]).finally(() => {
    ActionsPanel.init(tableId, hallId, role, restaurantSlug);
    KazzaUI.hideLoading();
  });

  const toggleBtn = document.getElementById('toggle-header-btn');
  const headerContainer = document.getElementById('header-container');
  let headerVisible = true;

  toggleBtn.addEventListener('click', () => {
    headerVisible = !headerVisible;
    headerContainer.classList.toggle('hidden', !headerVisible);
    toggleBtn.textContent = headerVisible ? '▲' : '▼';
  });

  const mobileTabs = document.getElementById('mobile-tabs');
  const contentContainer = document.getElementById('content-container');

  function handleResize() {
    const isMobile = window.innerWidth <= 1024;
    mobileTabs.classList.toggle('hidden', !isMobile);
    if (!isMobile) {
      contentContainer.classList.remove('mobile-orders', 'mobile-menu');
    } else {
      contentContainer.classList.add('mobile-orders');
    }
  }

  mobileTabs.querySelectorAll('.tab-button').forEach((btn) => {
    btn.addEventListener('click', () => {
      mobileTabs.querySelectorAll('.tab-button').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      contentContainer.classList.remove('mobile-orders', 'mobile-menu');
      contentContainer.classList.add(
        btn.dataset.tab === 'orders' ? 'mobile-orders' : 'mobile-menu'
      );
    });
  });

  window.addEventListener('resize', handleResize);
  handleResize();
})();
