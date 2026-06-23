const StatisticsPage = {
  shiftInfo: null,

  async init() {
    this.bindEvents();
    await this.refresh();
    setInterval(() => this.loadActiveOrders(), 30000);
  },

  bindEvents() {
    document.getElementById('btn-start-shift')?.addEventListener('click', () => this.showStartModal());
    document.getElementById('btn-end-shift')?.addEventListener('click', () => this.showEndModal());
    document.getElementById('btn-refresh')?.addEventListener('click', () => this.run('calculate-till-now'));
    document.getElementById('btn-daily')?.addEventListener('click', () => this.run('calculate-daily'));
    document.getElementById('btn-monthly')?.addEventListener('click', () => this.run('calculate-monthly'));
    document.getElementById('btn-yearly')?.addEventListener('click', () => this.run('calculate-yearly'));
    document.getElementById('btn-waitress')?.addEventListener('click', () => this.run('calculate-per-waitress'));
  },

  async refresh() {
    await AdminUI.withLoading(async () => {
      await this.loadActiveOrders();
      try {
        this.shiftInfo = await AdminAPI.statistics.get('current-shift-info');
      } catch { this.shiftInfo = null; }
      this.updateShiftUI();
    });
  },

  updateShiftUI() {
    const startBtn = document.getElementById('btn-start-shift');
    const endBtn = document.getElementById('btn-end-shift');
    const shiftCards = document.getElementById('shift-cards');
    if (this.shiftInfo) {
      startBtn?.classList.add('hidden');
      endBtn?.classList.remove('hidden');
      if (shiftCards) {
        shiftCards.innerHTML = `
          <div class="stat-card"><div class="label">Nağd (növbə)</div><div class="value">${this.shiftInfo.cash_total} AZN</div></div>
          <div class="stat-card"><div class="label">Cəmi (növbə)</div><div class="value">${this.shiftInfo.total} AZN</div></div>`;
      }
    } else {
      startBtn?.classList.remove('hidden');
      endBtn?.classList.add('hidden');
      if (shiftCards) shiftCards.innerHTML = '';
    }
  },

  async loadActiveOrders() {
    try {
      const data = await AdminAPI.statistics.get('active-orders');
      document.getElementById('stat-paid').textContent = `${data.total_paid} AZN`;
      document.getElementById('stat-unpaid').textContent = `${data.total_unpaid} AZN`;
    } catch (_) {}
  },

  async run(action, data = {}) {
    try {
      const res = await AdminUI.withLoading(() => AdminAPI.statistics.post(action, data));
      AdminUI.toast(res.detail || 'Tamamlandı', 'success');
      await this.refresh();
    } catch (e) { AdminUI.toast(e.message, 'error'); }
  },

  async showStartModal() {
    let info = { initial_cash: '0', initial_card: '0', initial_other: '0' };
    try { info = await AdminAPI.statistics.get('start-shift-info'); } catch (_) {}
    const modal = AdminUI.openModal('Növbəni Başlat', `
      <div class="form-group"><label>Başlanğıc nağd</label><input type="number" step="0.01" id="m-cash" value="${info.initial_cash}"></div>
      <div class="form-group"><label>Başlanğıc kart</label><input type="number" step="0.01" id="m-card" value="${info.initial_card}"></div>
      <div class="form-group"><label>Başlanğıc digər</label><input type="number" step="0.01" id="m-other" value="${info.initial_other}"></div>
      <button class="btn btn-primary" id="m-submit">Başlat</button>`);
    modal.querySelector('#m-submit').onclick = async () => {
      await this.run('start-shift', {
        initial_cash: modal.querySelector('#m-cash').value,
        initial_card: modal.querySelector('#m-card').value,
        initial_other: modal.querySelector('#m-other').value,
      });
      modal.remove();
    };
  },

  showEndModal() {
    if (!this.shiftInfo) return;
    const modal = AdminUI.openModal('Növbəni Bağla', `
      <div class="alert info">Nağd: ${this.shiftInfo.cash_in_hand} AZN · Kart: ${this.shiftInfo.card_total} AZN</div>
      <div class="form-group"><label>Götürülən məbləğ</label><input type="number" step="0.01" id="m-withdrawn" value="0"></div>
      <div class="form-group"><label>Qeydlər</label><input type="text" id="m-notes"></div>
      <button class="btn btn-danger" id="m-submit">Növbəni Bağla</button>`);
    modal.querySelector('#m-submit').onclick = async () => {
      await this.run('end-shift', {
        shift_id: this.shiftInfo.shift_id,
        withdrawn_amount: modal.querySelector('#m-withdrawn').value,
        withdrawn_notes: modal.querySelector('#m-notes').value,
      });
      modal.remove();
    };
  },
};

document.addEventListener('DOMContentLoaded', async () => {
  await StatisticsPage.init();
  ModelList.init('orders', 'statistics');
});
