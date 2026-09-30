const ActionsPanel = {
  tableId: null,
  hallId: null,
  role: null,
  restaurantSlug: '',
  totalPrice: 0,
  printCheck: false,
  mainOrderId: null,

  ACTIONS: [
    { id: 1, label: 'Hesab Çeki', method: 'printOrder', style: 'primary' },
    { id: 5, label: 'Çeki ləğv et', method: 'cancelPrintOrder', style: 'danger' },
    { id: 7, label: 'Hazırla', method: 'confirmKitchen', style: 'success' },
    { id: 3, label: 'Ödəniş', method: 'cancelOrder', style: 'primary' },
    { id: 2, label: 'Ofsianti dəyiş', method: 'changeWaitress', style: '' },
    { id: 4, label: 'Masanı köçür', method: 'openTransferModal', style: '' },
    { id: 6, label: 'Masanı birləşdir', method: 'openCombine', style: '' },
  ],

  init(tableId, hallId, role, restaurantSlug = '') {
    this.tableId = tableId;
    this.hallId = hallId;
    this.role = role;
    this.restaurantSlug = restaurantSlug;

    const container = document.getElementById('admin-actions');
    if (container && !container.dataset.actionsBound) {
      container.dataset.actionsBound = '1';
      container.addEventListener('click', (e) => {
        const btn = e.target.closest('.action-button');
        if (!btn) return;
        this.handleAction(btn.dataset.method);
      });
    }

    this.render();
  },

  filteredActions() {
    if (this.role === 'admin' || this.role === 'restaurant') return this.ACTIONS;
    if (this.role === 'waitress' || this.role === 'captain_waitress') {
      return this.ACTIONS.filter((a) => a.id === 1 || a.id === 7);
    }
    return [];
  },

  setTotalPrice(price) { this.totalPrice = price; },

  setPrintCheck(val) {
    this.printCheck = val;
    this.render();
  },

  async loadMainOrderId() {
    const orders = await KazzaAPI.listOrders(this.tableId);
    const main = orders.find((o) => o.is_main);
    this.mainOrderId = main ? main.pk : this.tableId;
  },

  showLoading(show, message) {
    if (show) KazzaUI.showLoading(message || 'Emal edilir...');
    else KazzaUI.hideLoading();
  },

  toast(msg, type = 'error') {
    if (type === 'success') KazzaUI.success(msg);
    else KazzaUI.error(msg);
  },

  render() {
    const container = document.getElementById('admin-actions');
    if (!container) return;

    const actions = this.filteredActions();
    if (actions.length === 0) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = actions.map((action) => {
      let cls = 'action-button';
      if (action.method === 'printOrder' && this.printCheck) cls += ' action-button--success';
      else if (action.style === 'success') cls += ' action-button--success';
      else if (action.style === 'danger') cls += ' action-button--danger';
      else if (action.style === 'primary') cls += ' action-button--primary';
      return `<button class="${cls}" data-method="${action.method}">${action.label}</button>`;
    }).join('');
  },

  async handleAction(method) {
    switch (method) {
      case 'printOrder': return this.doPrintCheck();
      case 'cancelPrintOrder': return this.doCancelPrint();
      case 'confirmKitchen': return this.doConfirmKitchen();
      case 'cancelOrder': return this.showPaymentModal();
      case 'changeWaitress': return this.showWaitressModal();
      case 'openTransferModal': return this.showTransferModal();
      case 'openCombine': return this.showCombineModal();
    }
  },

  async doPrintCheck() {
    this.showLoading(true, 'Çek çap edilir...');
    try {
      await KazzaAPI.printCheck(this.tableId);
      this.setPrintCheck(true);
      this.toast('Hesab çeki uğurla çap edildi', 'success');
    } catch (e) {
      this.toast(KazzaUI.parseError(e, 'Çek çap edilə bilmədi.'));
    }
    this.showLoading(false);
  },

  async doCancelPrint() {
    this.showLoading(true, 'Çek ləğv edilir...');
    try {
      await KazzaAPI.deleteCheck(this.tableId);
      this.setPrintCheck(false);
      this.toast('Çek uğurla ləğv edildi', 'success');
    } catch (e) {
      this.toast(KazzaUI.parseError(e, 'Çek ləğv edilə bilmədi.'));
    }
    this.showLoading(false);
  },

  async doConfirmKitchen() {
    this.showLoading(true, 'Mətbəxə göndərilir...');
    try {
      await this.loadMainOrderId();
      await KazzaAPI.confirmOrder(this.tableId, this.mainOrderId);
      EventBus.emit('order-confirmed');
      this.toast('Sifariş mətbəxə göndərildi', 'success');
    } catch (e) {
      this.toast(KazzaUI.parseError(e, 'Sifariş təsdiqlənə bilmədi.'));
    }
    this.showLoading(false);
  },

  showPaymentModal() {
    const overlay = document.getElementById('popup-overlay');
    overlay.classList.remove('hidden');

    const state = {
      cash: '', card: '', other: '',
      discountAmount: 0, discountComment: '',
      activeInput: 'cash',
    };

    const readDiscount = () => {
      const amt = document.getElementById('discount-amt');
      const comment = document.getElementById('discount-comment');
      if (amt) state.discountAmount = parseFloat(amt.value) || 0;
      if (comment) state.discountComment = comment.value;
    };

    const escAttr = (value) => String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;');

    const paymentTypes = [
      { key: 'cash', label: 'Nağd', fill: 'Tam nağd' },
      { key: 'card', label: 'Kart', fill: 'Tam kart' },
      { key: 'other', label: 'Digər', fill: 'Tam digər' },
    ];

    const render = () => {
      readDiscount();
      const total = this.totalPrice;
      const discount = state.discountAmount || 0;
      const finalAmount = Math.max(0, total - discount);
      const paid = (parseFloat(state.cash) || 0)
        + (parseFloat(state.card) || 0)
        + (parseFloat(state.other) || 0);
      const remaining = paid - finalAmount;

      overlay.innerHTML = `
        <div class="modal-dialog modal-dialog--payment">
          <h3 class="modal-title">Ödəniş</h3>
          <div class="payment-summary">
            <div class="payment-summary-item">
              <div class="label">Ümumi</div>
              <div class="value">₼ ${total.toFixed(2)}</div>
            </div>
            <div class="payment-summary-item">
              <div class="label">Son məbləğ</div>
              <div class="value" id="pay-final">₼ ${finalAmount.toFixed(2)}</div>
            </div>
            <div class="payment-summary-item">
              <div class="label">Ödənilən</div>
              <div class="value" id="pay-paid">₼ ${paid.toFixed(2)}</div>
            </div>
            <div class="payment-summary-item">
              <div class="label">Qalıq</div>
              <div class="value" id="pay-remaining" style="color:${remaining >= 0 ? 'var(--primary-dark)' : 'var(--danger)'}">
                ₼ ${remaining.toFixed(2)}
              </div>
            </div>
          </div>
          <div class="payment-methods">
            ${paymentTypes.map((type) => `
              <div class="payment-method ${state.activeInput === type.key ? 'is-active' : ''}">
                <span class="payment-label">${type.label}</span>
                <div class="payment-field">
                  <span class="payment-currency">₼</span>
                  <input class="payment-amount" readonly inputmode="decimal"
                         placeholder="0.00" value="${escAttr(state[type.key])}" data-type="${type.key}">
                </div>
                <button type="button" class="payment-fill-btn" data-fill="${type.key}">${type.fill}</button>
              </div>
            `).join('')}
          </div>
          <div class="numpad-buttons" id="pay-numpad">
            ${[1,2,3,4,5,6,7,8,9,'.',0,'←'].map((n) =>
              `<button type="button" data-key="${n}">${n}</button>`).join('')}
          </div>
          <div class="modal-form">
            <label>Endirim (₼)
              <input type="text" id="discount-amt" inputmode="decimal" value="${discount || ''}" placeholder="0.00">
            </label>
            <label>Endirim səbəbi
              <input type="text" id="discount-comment" value="${escAttr(state.discountComment)}" placeholder="Qeyd yazın...">
            </label>
          </div>
          <div class="modal-buttons">
            <button class="cancel-btn" id="pay-cancel">Ləğv et</button>
            <button class="confirm-btn" id="pay-confirm">Təsdiqlə</button>
          </div>
        </div>`;

      overlay.querySelectorAll('[data-type]').forEach((inp) => {
        inp.addEventListener('click', () => { state.activeInput = inp.dataset.type; render(); });
      });

      overlay.querySelectorAll('[data-fill]').forEach((btn) => {
        btn.addEventListener('click', () => {
          readDiscount();
          const amount = Math.max(0, this.totalPrice - (state.discountAmount || 0));
          state.cash = '';
          state.card = '';
          state.other = '';
          state[btn.dataset.fill] = amount.toFixed(2);
          state.activeInput = btn.dataset.fill;
          render();
        });
      });

      overlay.querySelector('#discount-amt').addEventListener('input', () => {
        const discountNow = parseFloat(document.getElementById('discount-amt').value) || 0;
        const finalNow = Math.max(0, this.totalPrice - discountNow);
        const paidNow = (parseFloat(state.cash) || 0)
          + (parseFloat(state.card) || 0)
          + (parseFloat(state.other) || 0);
        const remainingNow = paidNow - finalNow;
        document.getElementById('pay-final').textContent = `₼ ${finalNow.toFixed(2)}`;
        const remEl = document.getElementById('pay-remaining');
        remEl.textContent = `₼ ${remainingNow.toFixed(2)}`;
        remEl.style.color = remainingNow >= 0 ? 'var(--primary-dark)' : 'var(--danger)';
      });

      overlay.querySelector('#pay-numpad').addEventListener('click', (e) => {
        const key = e.target.closest('button')?.dataset.key;
        if (!key) return;
        const field = state.activeInput;
        let next = state[field] || '';
        if (key === '←') next = next.slice(0, -1);
        else if (key === '.' && next.includes('.')) return;
        else next += key;
        state[field] = next;
        render();
      });

      overlay.querySelector('#pay-cancel').onclick = () => {
        overlay.classList.add('hidden');
        overlay.innerHTML = '';
      };

      overlay.querySelector('#pay-confirm').onclick = async () => {
        state.discountAmount = parseFloat(document.getElementById('discount-amt').value) || 0;
        state.discountComment = document.getElementById('discount-comment').value;
        const cash = parseFloat(state.cash) || 0;
        const card = parseFloat(state.card) || 0;
        const other = parseFloat(state.other) || 0;
        const methods = [];
        if (cash > 0) methods.push({ payment_type: 'cash', amount: cash });
        if (card > 0) methods.push({ payment_type: 'card', amount: card });
        if (other > 0) methods.push({ payment_type: 'other', amount: other });

        if (methods.length === 0) {
          KazzaUI.warning('Zəhmət olmasa ödəniş məbləğini daxil edin.');
          return;
        }

        const btn = overlay.querySelector('#pay-confirm');
        btn.disabled = true;
        btn.textContent = 'Emal edilir...';
        KazzaUI.showLoading('Ödəniş həyata keçirilir...');

        try {
          await KazzaAPI.cancelPayment(this.tableId, {
            payment_methods: methods,
            paid_amount: cash + card + other,
            discount_amount: state.discountAmount,
            discount_comment: state.discountComment,
          });
          overlay.classList.add('hidden');
          overlay.innerHTML = '';
          KazzaUI.success('Ödəniş uğurla tamamlandı!');
          setTimeout(() => { window.location.href = `/r/${this.restaurantSlug}/hall/${this.hallId}/`; }, 800);
        } catch (e) {
          KazzaUI.error(KazzaUI.parseError(e, 'Ödəniş zamanı xəta baş verdi.'));
          btn.disabled = false;
          btn.textContent = 'Təsdiqlə';
        } finally {
          KazzaUI.hideLoading();
        }
      };
    };

    render();
  },

  async showWaitressModal() {
    KazzaUI.showLoading('Ofsiantlar yüklənir...');
    let waitresses;
    try {
      waitresses = await KazzaAPI.fetchWaitresses();
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Ofsiant siyahısı yüklənə bilmədi.'));
      KazzaUI.hideLoading();
      return;
    }
    KazzaUI.hideLoading();

    const overlay = document.getElementById('popup-overlay');
    overlay.classList.remove('hidden');
    overlay.innerHTML = `
      <div class="modal-dialog">
        <h3 class="modal-title">Ofsianti dəyiş</h3>
        <div class="modal-form">
          <label>Ofsiant seçin
            <select id="waitress-select">
              ${waitresses.map((w) => `<option value="${w.id}">${w.full_name}</option>`).join('')}
            </select>
          </label>
        </div>
        <div class="modal-buttons">
          <button class="cancel-btn" id="w-cancel">Ləğv et</button>
          <button class="confirm-btn" id="w-confirm">Təsdiq et</button>
        </div>
      </div>`;

    overlay.querySelector('#w-cancel').onclick = () => {
      overlay.classList.add('hidden');
      overlay.innerHTML = '';
    };
    overlay.querySelector('#w-confirm').onclick = async () => {
      const id = parseInt(document.getElementById('waitress-select').value, 10);
      KazzaUI.showLoading('Ofsiant dəyişdirilir...');
      try {
        await KazzaAPI.changeWaitressForOrder(this.tableId, id);
        overlay.classList.add('hidden');
        overlay.innerHTML = '';
        KazzaUI.success('Ofsiant uğurla dəyişdirildi');
      } catch (e) {
        KazzaUI.error(KazzaUI.parseError(e, 'Ofsiant dəyişdirilə bilmədi.'));
      } finally {
        KazzaUI.hideLoading();
      }
    };
  },

  async showTransferModal() {
    KazzaUI.showLoading('Zallar yüklənir...');
    let rooms;
    try {
      rooms = await KazzaAPI.fetchRooms();
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e));
      KazzaUI.hideLoading();
      return;
    }
    KazzaUI.hideLoading();

    const overlay = document.getElementById('popup-overlay');
    overlay.classList.remove('hidden');
    overlay.innerHTML = `
      <div class="modal-dialog">
        <h3 class="modal-title">Masanı köçür</h3>
        <div class="modal-form">
          <label>Zal <select id="transfer-hall">${rooms.map((r) => `<option value="${r.id}">${r.name}</option>`).join('')}</select></label>
          <label>Masa <select id="transfer-table"></select></label>
        </div>
        <div class="modal-buttons">
          <button class="cancel-btn" id="t-cancel">Ləğv et</button>
          <button class="confirm-btn" id="t-confirm">Köçür</button>
        </div>
      </div>`;

    const loadTables = async () => {
      const hallId = parseInt(document.getElementById('transfer-hall').value, 10);
      try {
        const tables = await KazzaAPI.fetchTablesByHallId(hallId);
        document.getElementById('transfer-table').innerHTML = tables.map(
          (t) => `<option value="${t.id}">Masa ${t.number}</option>`
        ).join('');
      } catch (e) {
        KazzaUI.error(KazzaUI.parseError(e, 'Masalar yüklənə bilmədi.'));
      }
    };

    document.getElementById('transfer-hall').addEventListener('change', loadTables);
    await loadTables();

    overlay.querySelector('#t-cancel').onclick = () => {
      overlay.classList.add('hidden');
      overlay.innerHTML = '';
    };
    overlay.querySelector('#t-confirm').onclick = async () => {
      const newId = parseInt(document.getElementById('transfer-table').value, 10);
      KazzaUI.showLoading('Masa köçürülür...');
      try {
        await KazzaAPI.changeTableForOrder(this.tableId, newId);
        overlay.classList.add('hidden');
        overlay.innerHTML = '';
        KazzaUI.success('Masa uğurla köçürüldü');
        setTimeout(() => { window.location.href = `/r/${this.restaurantSlug}/hall/${this.hallId}/table/${newId}/`; }, 600);
      } catch (e) {
        KazzaUI.error(KazzaUI.parseError(e, 'Masa köçürülə bilmədi.'));
      } finally {
        KazzaUI.hideLoading();
      }
    };
  },

  async showCombineModal() {
    KazzaUI.showLoading('Zallar yüklənir...');
    let rooms;
    try {
      rooms = await KazzaAPI.fetchRooms();
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e));
      KazzaUI.hideLoading();
      return;
    }
    KazzaUI.hideLoading();

    const overlay = document.getElementById('popup-overlay');
    overlay.classList.remove('hidden');
    overlay.innerHTML = `
      <div class="modal-dialog">
        <h3 class="modal-title">Masanı birləşdir</h3>
        <div class="modal-form">
          <label>Zal <select id="combine-hall">${rooms.map((r) => `<option value="${r.id}">${r.name}</option>`).join('')}</select></label>
          <label>Masa <select id="combine-table"></select></label>
        </div>
        <div class="modal-buttons">
          <button class="cancel-btn" id="c-cancel">Ləğv et</button>
          <button class="confirm-btn" id="c-confirm">Birləşdir</button>
        </div>
      </div>`;

    const loadTables = async () => {
      const hallId = parseInt(document.getElementById('combine-hall').value, 10);
      try {
        const tables = await KazzaAPI.fetchTablesByHallId(hallId);
        const occupied = tables.filter((t) => t.waitress?.id !== 0);
        if (occupied.length === 0) {
          document.getElementById('combine-table').innerHTML = '<option value="">Dolu masa yoxdur</option>';
          return;
        }
        document.getElementById('combine-table').innerHTML = occupied.map(
          (t) => `<option value="${t.id}">Masa ${t.number}</option>`
        ).join('');
      } catch (e) {
        KazzaUI.error(KazzaUI.parseError(e));
      }
    };

    document.getElementById('combine-hall').addEventListener('change', loadTables);
    await loadTables();

    overlay.querySelector('#c-cancel').onclick = () => {
      overlay.classList.add('hidden');
      overlay.innerHTML = '';
    };
    overlay.querySelector('#c-confirm').onclick = async () => {
      const otherId = parseInt(document.getElementById('combine-table').value, 10);
      if (!otherId) {
        KazzaUI.warning('Birləşdirmək üçün dolu masa seçin.');
        return;
      }
      KazzaUI.showLoading('Masalar birləşdirilir...');
      try {
        await KazzaAPI.combineTables(this.tableId, [otherId]);
        overlay.classList.add('hidden');
        overlay.innerHTML = '';
        KazzaUI.success('Masalar uğurla birləşdirildi');
        EventBus.emit('orderItemAdded');
      } catch (e) {
        KazzaUI.error(KazzaUI.parseError(e, 'Masalar birləşdirilə bilmədi.'));
      } finally {
        KazzaUI.hideLoading();
      }
    };
  },
};

window.ActionsPanel = ActionsPanel;
