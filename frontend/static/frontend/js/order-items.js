const OrderItems = {
  tableId: null,
  role: null,
  mainOrder: null,
  otherOrders: [],
  orderItems: [],
  showDropdown: null,
  selectedOrderId: null,
  isLoading: false,

  init(tableId, role) {
    this.tableId = tableId;
    this.role = role;
    EventBus.on('orderItemAdded', () => this.refresh());
    EventBus.on('order-confirmed', () => this.refresh());
    return this.load();
  },

  isAdmin() {
    return this.role === 'admin' || this.role === 'restaurant';
  },

  showSkeleton() {
    const container = document.getElementById('order-items');
    if (container) {
      container.innerHTML = KazzaUI.skeletonCards(3, 'card');
    }
  },

  async load() {
    this.showSkeleton();
    try {
      await this.fetchOrders();
      if (this.mainOrder) {
        this.showDropdown = this.mainOrder.pk;
        this.selectedOrderId = this.mainOrder.pk;
        EventBus.emit('selectedOrderId', this.mainOrder.pk);
        await this.fetchOrderItems(this.mainOrder.pk);
      }
      this.render();
    } catch (e) {
      const container = document.getElementById('order-items');
      container.innerHTML = KazzaUI.emptyState('📋', 'Sifarişlər yüklənə bilmədi', 'Yenidən cəhd edin');
      KazzaUI.error(KazzaUI.parseError(e, 'Sifarişlər yüklənərkən xəta baş verdi.'));
    }
  },

  async refresh() {
    try {
      await this.fetchOrders();
      if (this.selectedOrderId) {
        await this.fetchOrderItems(this.selectedOrderId);
      }
      this.render();
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e));
    }
  },

  async fetchOrders() {
    const orders = await KazzaAPI.listOrders(this.tableId);
    this.mainOrder = orders.find((o) => o.is_main) || null;
    this.otherOrders = orders.filter((o) => !o.is_main);
  },

  async fetchOrderItems(orderId) {
    this.selectedOrderId = orderId;
    this.orderItems = await KazzaAPI.listOrderItems(this.tableId, orderId);
    this.orderItems.forEach((item) => { item.orderId = orderId; });
  },

  getTotalPrice() {
    return this.orderItems.reduce(
      (sum, item) => sum + item.meal.price * item.quantity, 0
    ).toFixed(2);
  },

  async toggleDropdown(orderId) {
    if (this.showDropdown === orderId) {
      this.showDropdown = null;
      EventBus.emit('selectedOrderId', null);
    } else {
      this.showDropdown = orderId;
      if (orderId !== 'default') {
        EventBus.emit('selectedOrderId', orderId);
        try {
          await this.fetchOrderItems(orderId);
        } catch (e) {
          KazzaUI.error(KazzaUI.parseError(e));
        }
      } else {
        this.orderItems = [];
        EventBus.emit('selectedOrderId', null);
      }
    }
    this.render();
  },

  async incrementQuantity(item) {
    try {
      await KazzaAPI.addOrderItem(this.tableId, item.meal.id, 1, item.orderId);
      KazzaUI.success(`${item.meal.name} əlavə edildi`);
      EventBus.emit('orderItemAdded');
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Məhsul əlavə edilə bilmədi.'));
    }
  },

  async decrementQuantity(item) {
    if (item.quantity <= 0) return;
    try {
      await KazzaAPI.deleteOrderItem(this.tableId, {
        order_id: item.orderId,
        meal_id: item.meal.id,
        quantity: 1,
        order_item_id: item.order_item_id,
      });
      if (item.quantity - 1 <= 0) {
        window.location.reload();
        return;
      }
      EventBus.emit('orderItemAdded');
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Məhsul silinə bilmədi.'));
    }
  },

  renderOrderDropdown() {
    const total = this.getTotalPrice();

    if (this.orderItems.length === 0) {
      return `
        <div class="order-dropdown">
          ${KazzaUI.emptyState('🍽', 'Sifariş boşdur', 'Menyudan məhsul əlavə edin')}
        </div>`;
    }

    const rows = this.orderItems.map((item, index) => {
      const canIncrement = item.order_item_id === 0;
      const canDecrement = this.isAdmin() && !item.confirmed;
      const statusBadge = item.confirmed
        ? '<span class="status-badge status-badge--confirmed">✓ Hazır</span>'
        : '<span class="status-badge status-badge--waiting">⏳ Gözləyir</span>';

      return `
        <tr>
          <td>
            <strong>${item.meal.name}</strong>
            ${item.comment ? `<br><small style="color:var(--text-muted)">${item.comment}</small>` : ''}
          </td>
          <td>
            <div class="item-actions">
              ${canDecrement ? `<button class="minus" data-action="dec" data-item-index="${index}">−</button>` : ''}
              <span style="min-width:20px;text-align:center;font-weight:700">${item.quantity}</span>
              ${canIncrement ? `<button class="plus" data-action="inc" data-item-index="${index}">+</button>` : ''}
            </div>
          </td>
          <td>₼${item.meal.price}</td>
          <td><strong>₼${(item.meal.price * item.quantity).toFixed(2)}</strong></td>
          <td>${statusBadge}</td>
          <td>
            ${!item.confirmed ? `<button class="action-chip" data-action="comment" data-item-index="${index}">Qeyd</button>` : ''}
            ${this.isAdmin() && item.confirmed ? `<button class="action-chip" data-action="return" data-item-index="${index}">Qaytar</button>` : ''}
          </td>
        </tr>`;
    }).join('');

    return `
      <div class="order-dropdown">
        <table class="order-table">
          <thead><tr><th>Ad</th><th>Say</th><th>Qiymət</th><th>Cəmi</th><th>Status</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <div style="padding:12px 16px;background:var(--primary-light);border-radius:var(--radius);margin-top:8px;display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600;color:var(--text-secondary)">Sifariş cəmi</span>
          <span style="font-weight:800;font-size:1.1rem;color:var(--primary-dark)">₼ ${total}</span>
        </div>
      </div>`;
  },

  renderOrderBox(order, label) {
    const orderId = order ? order.pk : 'default';
    const isOpen = this.showDropdown === orderId;
    return `
      <div class="order-item-box">
        <button class="order-button" data-order-id="${orderId}">
          <span>${label}</span>
          ${isOpen ? `<span class="order-button-total">₼ ${this.getTotalPrice()}</span>` : ''}
        </button>
        ${isOpen ? this.renderOrderDropdown() : ''}
      </div>`;
  },

  render() {
    const container = document.getElementById('order-items');
    if (!container) return;

    let html = '';
    if (this.mainOrder) {
      html += this.renderOrderBox(this.mainOrder, `Sifariş #${this.mainOrder.pk}`);
    }
    this.otherOrders.forEach((order) => {
      html += this.renderOrderBox(order, `Sifariş #${order.pk}`);
    });
    if (!this.mainOrder && this.otherOrders.length === 0) {
      html = KazzaUI.emptyState('📋', 'Hələ sifariş yoxdur', 'Sağ tərəfdən menyu seçib məhsul əlavə edin');
    }
    container.innerHTML = html;

    container.querySelectorAll('.order-button').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.orderId;
        this.toggleDropdown(id === 'default' ? 'default' : parseInt(id, 10));
      });
    });

    this._bindItemActions(container);
  },

  _bindItemActions(container) {
    const findItem = (btn) => this.orderItems[parseInt(btn.dataset.itemIndex, 10)];

    container.querySelectorAll('[data-action="inc"]').forEach((btn) => {
      btn.addEventListener('click', () => { const item = findItem(btn); if (item) this.incrementQuantity(item); });
    });
    container.querySelectorAll('[data-action="dec"]').forEach((btn) => {
      btn.addEventListener('click', () => { const item = findItem(btn); if (item) this.decrementQuantity(item); });
    });
    container.querySelectorAll('[data-action="comment"]').forEach((btn) => {
      btn.addEventListener('click', () => { const item = findItem(btn); if (item) this.showCommentModal(item); });
    });
    container.querySelectorAll('[data-action="return"]').forEach((btn) => {
      btn.addEventListener('click', () => { const item = findItem(btn); if (item) this.showReturnModal(item); });
    });
  },

  showCommentModal(item) {
    const overlay = document.getElementById('popup-overlay');
    overlay.classList.remove('hidden');
    overlay.innerHTML = `
      <div class="modal-dialog">
        <h3 class="modal-title">Qeyd əlavə et</h3>
        <p style="color:var(--text-muted);margin-bottom:16px;font-size:0.875rem">${item.meal.name}</p>
        <div class="modal-form">
          <label>Qeyd
            <textarea id="comment-input" rows="3" placeholder="Məs: soğansız..."></textarea>
          </label>
        </div>
        <div class="modal-buttons">
          <button class="cancel-btn" id="comment-cancel">Ləğv et</button>
          <button class="confirm-btn" id="comment-save">Saxla</button>
        </div>
      </div>`;

    overlay.querySelector('#comment-cancel').onclick = () => {
      overlay.classList.add('hidden');
      overlay.innerHTML = '';
    };
    overlay.querySelector('#comment-save').onclick = async () => {
      const comment = document.getElementById('comment-input').value.trim();
      if (!comment) {
        KazzaUI.warning('Zəhmət olmasa qeyd yazın.');
        return;
      }
      KazzaUI.showLoading('Qeyd saxlanılır...');
      try {
        await KazzaAPI.commentOrderItem(this.tableId, item.meal.id, comment, item.orderId);
        overlay.classList.add('hidden');
        overlay.innerHTML = '';
        KazzaUI.success('Qeyd əlavə edildi');
        EventBus.emit('orderItemAdded');
      } catch (e) {
        KazzaUI.error(KazzaUI.parseError(e));
      } finally {
        KazzaUI.hideLoading();
      }
    };
  },

  showReturnModal(item) {
    const overlay = document.getElementById('popup-overlay');
    overlay.classList.remove('hidden');
    overlay.innerHTML = `
      <div class="modal-dialog">
        <h3 class="modal-title">Məhsul qaytarma</h3>
        <p style="color:var(--text-muted);margin-bottom:16px;font-size:0.875rem">${item.meal.name}</p>
        <div class="modal-form">
          <label>Səbəb
            <select id="return-reason">
              <option value="return">Müştəri qaytardı</option>
              <option value="waste">Tullantı / korlandı</option>
            </select>
          </label>
          <label>Qeyd
            <input type="text" id="return-comment" placeholder="Əlavə qeyd...">
          </label>
        </div>
        <div class="modal-buttons">
          <button class="cancel-btn" id="return-cancel">Ləğv et</button>
          <button class="confirm-btn" id="return-save">Təsdiq et</button>
        </div>
      </div>`;

    overlay.querySelector('#return-cancel').onclick = () => {
      overlay.classList.add('hidden');
      overlay.innerHTML = '';
    };
    overlay.querySelector('#return-save').onclick = async () => {
      KazzaUI.showLoading('Qaytarma emal edilir...');
      try {
        await KazzaAPI.deleteOrderItem(this.tableId, {
          order_id: item.orderId,
          meal_id: item.meal.id,
          quantity: 1,
          reason: document.getElementById('return-reason').value,
          reason_comment: document.getElementById('return-comment').value,
          confirmed: true,
          order_item_id: item.order_item_id,
        });
        overlay.classList.add('hidden');
        overlay.innerHTML = '';
        KazzaUI.success('Məhsul qaytarıldı');
        EventBus.emit('orderItemAdded');
      } catch (e) {
        KazzaUI.error(KazzaUI.parseError(e));
      } finally {
        KazzaUI.hideLoading();
      }
    };
  },
};

window.OrderItems = OrderItems;
