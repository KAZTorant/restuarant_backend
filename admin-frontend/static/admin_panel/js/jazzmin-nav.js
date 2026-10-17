document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.nav-sidebar');
  if (!nav || document.getElementById('sales-analytics-nav')) return;

  const item = document.createElement('li');
  item.className = 'nav-item';
  item.id = 'sales-analytics-nav';
  const active = window.location.pathname.indexOf('/admin/analytics') === 0 ? ' active' : '';
  item.innerHTML = `<a href="/admin/analytics/" class="nav-link${active}"><i class="nav-icon fas fa-chart-bar"></i><p>Satış paneli</p></a>`;

  const dashboard = nav.querySelector(':scope > .nav-item');
  if (dashboard) dashboard.insertAdjacentElement('afterend', item);
  else nav.prepend(item);
});
