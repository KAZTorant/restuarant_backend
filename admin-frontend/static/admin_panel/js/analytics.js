const AnalyticsPage = {
  range: 'day',
  productSort: 'revenue',
  products: [],

  money(value) {
    return `${new Intl.NumberFormat('az-AZ', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value || 0)} AZN`;
  },

  num(value) {
    return new Intl.NumberFormat('az-AZ').format(value || 0);
  },

  async load() {
    const params = { range: this.range };
    const restaurant = document.getElementById('restaurant-select')?.value;
    if (restaurant) params.restaurant = restaurant;
    if (this.range === 'custom') {
      params.start = document.getElementById('date-start').value;
      params.end = document.getElementById('date-end').value;
      if (!params.start || !params.end) {
        AdminUI.toast('Başlanğıc və bitiş tarixini seçin', 'error');
        return;
      }
    }

    AdminUI.showLoading();
    try {
      const data = await AdminAPI.analytics(params);
      this.render(data);
    } catch (e) {
      AdminUI.handleApiError(e, 'Satış paneli yüklənmədi');
    } finally {
      AdminUI.hideLoading();
    }
  },

  render(data) {
    this.renderRestaurant(data);
    const note = document.getElementById('scope-note');
    if (note) {
      note.textContent = data.scope_message || '';
      note.classList.toggle('hidden', !data.scope_message);
    }
    const label = document.getElementById('range-label');
    if (label) {
      const paid = data.paid_only ? ' · yalnız ödənilmiş' : '';
      const place = data.restaurant ? `${data.restaurant.name} · ` : '';
      label.textContent = `${place}${data.label}${paid} · ${this.formatStamp(data.start)} — ${this.formatStamp(data.end)}`;
    }
    const startInput = document.getElementById('date-start');
    const endInput = document.getElementById('date-end');
    if (startInput && data.start_date) startInput.value = data.start_date;
    if (endInput && data.end_date) endInput.value = data.end_date;

    document.querySelectorAll('#range-pills button').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.range === data.range);
    });

    const kpis = data.kpis || {};
    this.setText('kpi-revenue', this.money(kpis.revenue));
    this.setText('kpi-quantity', this.num(kpis.quantity));
    this.setText('kpi-orders', this.num(kpis.orders));
    this.setText('kpi-avg', this.money(kpis.avg_order));
    this.setText('kpi-customers', this.num(kpis.customers));
    this.setText('kpi-cash', this.money(kpis.cash));
    this.setText('kpi-card', this.money(kpis.card));
    this.setText('kpi-other', this.money(kpis.other));
    this.setText('kpi-paid', this.money(kpis.paid_total));
    this.setText('kpi-payments', this.num(kpis.payment_count));

    const trendTitle = document.getElementById('trend-title');
    if (trendTitle) trendTitle.textContent = data.hourly ? 'Saatlıq satış' : 'Günlük satış';
    if (data.needs_restaurant) {
      this.renderTrend([]);
      this.renderPayments([]);
      ['products', 'tables', 'waiters'].forEach((key) => {
        this.renderBars(`${key}-chart`, [], 'quantity', key, () => '');
        this.renderTable(`${key}-table`, [], [], () => 0);
      });
      return;
    }
    this.renderTrend(data.trend || []);
    this.renderPayments(data.payment_types || []);
    this.products = data.products || [];
    this.fillProductFilters();
    this.renderProductList();

    this.renderBars('tables-chart', data.tables, 'orders', 'tables', (row) => this.num(row.orders));
    this.renderTable('tables-table', data.tables, [
      ['Masa', (row) => row.name],
      ['Sifariş', (row) => this.num(row.orders)],
      ['Müştəri', (row) => this.num(row.customers)],
      ['Məbləğ', (row) => this.money(row.revenue)],
    ], (row) => row.share);

    this.renderBars('waiters-chart', data.waiters, 'orders', 'waiters', (row) => this.num(row.orders));
    this.renderTable('waiters-table', data.waiters, [
      ['Ofisiant', (row) => row.name],
      ['Sifariş', (row) => this.num(row.orders)],
      ['Məhsul', (row) => this.num(row.quantity)],
      ['Məbləğ', (row) => this.money(row.revenue)],
    ], (row) => row.share);
  },

  setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  },

  formatStamp(value) {
    if (!value) return '';
    const [date, time] = value.split('T');
    const [year, month, day] = date.split('-');
    return `${day}.${month}.${year} ${time || ''}`.trim();
  },

  renderRestaurant(data) {
    const wrap = document.getElementById('restaurant-wrap');
    const select = document.getElementById('restaurant-select');
    if (!wrap || !select) return;
    const options = data.restaurants || [];
    if (!options.length) {
      wrap.classList.add('hidden');
      return;
    }
    const selected = data.restaurant ? String(data.restaurant.id) : '';
    select.innerHTML = `<option value="">Restoran seçin</option>${options.map((row) => (
      `<option value="${row.id}">${AdminUI.escapeHtml(row.name)}</option>`
    )).join('')}`;
    select.value = selected;
    wrap.classList.remove('hidden');
  },

  renderTrend(points) {
    const el = document.getElementById('trend-chart');
    if (!el) return;
    const note = document.getElementById('scope-note')?.textContent;
    if (!points.length || !points.some((point) => point.revenue || point.quantity)) {
      el.innerHTML = `<div class="analytics-empty">${AdminUI.escapeHtml(note || 'Bu aralıqda satış yoxdur')}</div>`;
      return;
    }
    const max = Math.max(...points.map((p) => p.revenue), 0);
    const step = points.length > 16 ? Math.ceil(points.length / 8) : 1;
    el.innerHTML = points.map((point, index) => {
      const height = max ? Math.max((point.revenue / max) * 100, point.revenue ? 4 : 0) : 0;
      const showLabel = point.revenue || point.quantity || index % step === 0 || index === points.length - 1;
      return `
        <div class="vcol">
          <div class="vbar-wrap">
            <div class="vbar" style="height:${height}%">
              <span class="vbar-tip">${AdminUI.escapeHtml(point.label)} · ${this.money(point.revenue)} · ${this.num(point.quantity)} ədəd</span>
            </div>
          </div>
          <div class="vbar-label">${showLabel ? AdminUI.escapeHtml(point.label) : ''}</div>
        </div>`;
    }).join('');
  },

  renderBars(id, rows, metric, tone, formatValue) {
    const el = document.getElementById(id);
    if (!el) return;
    if (!rows || !rows.length) {
      el.innerHTML = '<div class="analytics-empty">Məlumat yoxdur</div>';
      return;
    }
    const chartRows = id === 'products-chart' ? rows.slice(0, 10) : rows;
    const max = Math.max(...chartRows.map((row) => Number(row[metric]) || 0), 0);
    el.innerHTML = chartRows.map((row) => {
      const width = max ? Math.max((Number(row[metric]) / max) * 100, 4) : 0;
      const barTone = row.tone || tone;
      return `
        <div class="hbar">
          <div class="hbar-label" title="${AdminUI.escapeHtml(row.name)}">${AdminUI.escapeHtml(row.name)}</div>
          <div class="hbar-track"><div class="hbar-fill ${barTone}" style="width:${width}%"></div></div>
          <div class="hbar-value">${formatValue(row)}</div>
        </div>`;
    }).join('');
  },

  renderPayments(rows) {
    const ordered = [...(rows || [])].sort((a, b) => (b.amount || 0) - (a.amount || 0));
    this.renderBars('payments-chart', ordered, 'amount', 'cash', (row) => this.money(row.amount));
    this.renderTable('payments-table', ordered, [
      ['Növ', (row) => row.name],
      ['Ödəniş', (row) => this.num(row.count)],
      ['Məbləğ', (row) => this.money(row.amount)],
    ], (row) => row.share);
  },

  fillProductFilters() {
    const groupSelect = document.getElementById('product-group');
    const categorySelect = document.getElementById('product-category');
    if (!groupSelect || !categorySelect) return;

    const groups = new Map();
    this.products.forEach((row) => {
      if (row.group_id != null) groups.set(String(row.group_id), row.group_name || 'Qrup');
    });
    const selectedGroup = groups.has(groupSelect.value) ? groupSelect.value : '';
    groupSelect.innerHTML = `<option value="">Bütün qruplar</option>${[...groups.entries()]
      .sort((a, b) => a[1].localeCompare(b[1], 'az'))
      .map(([id, name]) => `<option value="${id}">${AdminUI.escapeHtml(name)}</option>`)
      .join('')}`;
    groupSelect.value = selectedGroup;

    const categories = new Map();
    this.products.forEach((row) => {
      if (row.category_id == null) return;
      if (selectedGroup && String(row.group_id || '') !== selectedGroup) return;
      categories.set(String(row.category_id), row.category_name || 'Kateqoriya');
    });
    const selectedCategory = categories.has(categorySelect.value) ? categorySelect.value : '';
    categorySelect.innerHTML = `<option value="">Bütün kateqoriyalar</option>${[...categories.entries()]
      .sort((a, b) => a[1].localeCompare(b[1], 'az'))
      .map(([id, name]) => `<option value="${id}">${AdminUI.escapeHtml(name)}</option>`)
      .join('')}`;
    categorySelect.value = selectedCategory;
  },

  filteredProducts() {
    const groupId = document.getElementById('product-group')?.value || '';
    const categoryId = document.getElementById('product-category')?.value || '';
    return this.products.filter((row) => {
      if (groupId && String(row.group_id || '') !== groupId) return false;
      if (categoryId && String(row.category_id || '') !== categoryId) return false;
      return true;
    });
  },

  renderProductList() {
    const byQuantity = this.productSort === 'quantity';
    document.querySelectorAll('#product-sort button').forEach((button) => {
      button.classList.toggle('active', button.dataset.sort === this.productSort);
    });
    const source = this.filteredProducts();
    const totalRevenue = source.reduce((sum, row) => sum + (Number(row.revenue) || 0), 0);
    const totalQuantity = source.reduce((sum, row) => sum + (Number(row.quantity) || 0), 0);
    const rows = source
      .map((row) => ({
        ...row,
        share: totalRevenue ? Math.round((Number(row.revenue) / totalRevenue) * 1000) / 10 : 0,
        qty_share: totalQuantity ? Math.round((Number(row.quantity) / totalQuantity) * 1000) / 10 : 0,
      }))
      .sort((a, b) => {
        const left = byQuantity ? a.quantity : a.revenue;
        const right = byQuantity ? b.quantity : b.revenue;
        return (right || 0) - (left || 0);
      });
    this.renderBars(
      'products-chart',
      rows,
      byQuantity ? 'quantity' : 'revenue',
      'products',
      (row) => (byQuantity ? this.num(row.quantity) : this.money(row.revenue)),
    );
    this.renderTable('products-table', rows, [
      ['Məhsul', (row) => row.name],
      ['Miqdar', (row) => this.num(row.quantity)],
      ['Məbləğ', (row) => this.money(row.revenue)],
    ], (row) => (byQuantity ? row.qty_share : row.share));
  },

  renderTable(id, rows, columns, shareOf) {
    const el = document.getElementById(id);
    if (!el) return;
    if (!rows || !rows.length) {
      el.innerHTML = '<div class="analytics-empty">Məlumat yoxdur</div>';
      return;
    }
    const head = columns.map(([title]) => `<th>${title}</th>`).join('');
    const body = rows.map((row, index) => {
      const cells = columns.map(([, getter], colIndex) => {
        const value = getter(row);
        if (colIndex === 0) {
          const rankClass = index < 3 ? 'rank top' : 'rank';
          return `<td class="name"><span class="${rankClass}">${index + 1}</span> ${AdminUI.escapeHtml(String(value))}</td>`;
        }
        return `<td>${AdminUI.escapeHtml(String(value))}</td>`;
      }).join('');
      const share = shareOf(row) || 0;
      return `<tr>${cells}<td class="share-cell">${share}%<div class="share-bar"><span style="width:${Math.min(share, 100)}%"></span></div></td></tr>`;
    }).join('');
    el.innerHTML = `<table class="data-table analytics-table"><thead><tr>${head}<th>Pay</th></tr></thead><tbody>${body}</tbody></table>`;
  },

  init() {
    document.getElementById('range-pills')?.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-range]');
      if (!button) return;
      this.range = button.dataset.range;
      this.load();
    });
    document.getElementById('btn-apply')?.addEventListener('click', () => {
      this.range = 'custom';
      this.load();
    });
    document.getElementById('restaurant-select')?.addEventListener('change', () => this.load());
    document.getElementById('product-sort')?.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-sort]');
      if (!button) return;
      this.productSort = button.dataset.sort;
      this.renderProductList();
    });
    document.getElementById('product-group')?.addEventListener('change', () => {
      const categorySelect = document.getElementById('product-category');
      if (categorySelect) categorySelect.value = '';
      this.fillProductFilters();
      this.renderProductList();
    });
    document.getElementById('product-category')?.addEventListener('change', () => this.renderProductList());
    this.load();
  },
};

document.addEventListener('DOMContentLoaded', () => AnalyticsPage.init());
