const MenuPanel = {
  tableId: null,
  mealGroups: [],
  selectedGroup: null,
  selectedCategory: null,
  menuItems: [],
  showAllMeals: false,
  searchQuery: '',
  orderId: null,
  orderCreated: false,
  loading: false,

  init(tableId) {
    this.tableId = tableId;
    EventBus.on('selectedOrderId', (orderId) => { this.orderId = orderId; });
    return this.loadGroups();
  },

  async loadGroups() {
    const panel = document.getElementById('menu-panel');
    panel.innerHTML = `<div class="loading-inline"><div class="loading-spinner"></div> Menyu yüklənir...</div>`;
    try {
      this.mealGroups = await KazzaAPI.fetchMealGroups();
      this.render();
    } catch (e) {
      panel.innerHTML = KazzaUI.emptyState('🍽', 'Menyu yüklənə bilmədi', 'Yenidən cəhd edin');
      KazzaUI.error(KazzaUI.parseError(e, 'Menyu yüklənərkən xəta baş verdi.'));
    }
  },

  selectGroup(group) {
    this.selectedGroup = group;
    this.showAllMeals = true;
    this.selectedCategory = null;
    this.menuItems = [];
    this.render();
  },

  goBackToGroups() {
    this.showAllMeals = false;
    this.selectedGroup = null;
    this.selectedCategory = null;
    this.menuItems = [];
    this.searchQuery = '';
    this.render();
  },

  async fetchMenuItems(categoryId) {
    this.selectedCategory = categoryId;
    this.loading = true;
    this.render();
    try {
      this.menuItems = await KazzaAPI.fetchMealsByCategoryId(categoryId);
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Məhsullar yüklənə bilmədi.'));
      this.menuItems = [];
    }
    this.loading = false;
    this.render();
  },

  get filteredItems() {
    if (!this.searchQuery) return this.menuItems;
    const q = this.searchQuery.toLowerCase();
    return this.menuItems.filter((item) => item.name.toLowerCase().includes(q));
  },

  async ensureOrder() {
    if (!this.orderCreated) {
      try {
        await KazzaAPI.createOrder(this.tableId);
      } catch (e) {
        if (!e.response || e.response.status !== 400) throw e;
      }
      this.orderCreated = true;
    }
  },

  async handleItemClick(item) {
    if (this.loading) return;

    try {
      await this.ensureOrder();
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Sifariş yaradıla bilmədi.'));
      return;
    }

    if (item.is_extra) {
      this.showExtraPopup(item);
      return;
    }

    this.loading = true;
    this.render();
    try {
      await KazzaAPI.addOrderItem(this.tableId, item.id, 1, this.orderId);
      KazzaUI.success(`${item.name} sifarişə əlavə edildi`);
      EventBus.emit('orderItemAdded');
    } catch (e) {
      KazzaUI.error(KazzaUI.parseError(e, 'Məhsul əlavə edilə bilmədi.'));
    }
    this.loading = false;
    this.render();
  },

  showExtraPopup(item) {
    const overlay = document.getElementById('popup-overlay');
    overlay.classList.remove('hidden');
    overlay.innerHTML = `
      <div class="modal-dialog">
        <h3 class="modal-title">Extra məhsul</h3>
        <div class="modal-form">
          <label>Təsvir
            <input type="text" id="extra-desc" placeholder="Məhsul təsviri...">
          </label>
          <label>Qiymət (₼)
            <input type="text" id="extra-price" inputmode="decimal" placeholder="0.00">
          </label>
        </div>
        <div class="modal-buttons">
          <button class="cancel-btn" id="extra-cancel">Ləğv et</button>
          <button class="confirm-btn" id="extra-confirm">Əlavə et</button>
        </div>
      </div>`;

    overlay.querySelector('#extra-cancel').onclick = () => {
      overlay.classList.add('hidden');
      overlay.innerHTML = '';
    };
    overlay.querySelector('#extra-confirm').onclick = async () => {
      const desc = document.getElementById('extra-desc').value.trim();
      const price = parseFloat(document.getElementById('extra-price').value) || 0;
      if (!desc) {
        KazzaUI.warning('Zəhmət olmasa təsvir daxil edin.');
        return;
      }
      KazzaUI.showLoading('Məhsul əlavə edilir...');
      try {
        await KazzaAPI.addOrderItem(this.tableId, item.id, 1, this.orderId, desc, price);
        overlay.classList.add('hidden');
        overlay.innerHTML = '';
        KazzaUI.success('Extra məhsul əlavə edildi');
        EventBus.emit('orderItemAdded');
      } catch (e) {
        KazzaUI.error(KazzaUI.parseError(e));
      } finally {
        KazzaUI.hideLoading();
      }
    };
  },

  render() {
    const panel = document.getElementById('menu-panel');
    if (!panel) return;

    let tabsHtml = '';
    if (!this.showAllMeals || !this.selectedGroup) {
      tabsHtml = this.mealGroups.map((g) =>
        `<button class="menu-tab" data-group-id="${g.id}">${g.name}</button>`
      ).join('');
    } else {
      tabsHtml = `
        <button class="menu-tab menu-tab--back" id="back-to-groups">← Qruplar</button>
        ${this.selectedGroup.categories.map((c) =>
          `<button class="menu-tab ${this.selectedCategory === c.id ? 'active' : ''}" data-category-id="${c.id}">${c.name}</button>`
        ).join('')}`;
    }

    const searchHtml = (this.showAllMeals && this.selectedCategory)
      ? `<input type="text" class="search-input" id="menu-search" placeholder="🔍 Məhsul axtar..." value="${this.searchQuery}">`
      : '';

    let itemsContent = '';
    if (this.loading) {
      itemsContent = `<div class="loading-inline"><div class="loading-spinner"></div> Yüklənir...</div>`;
    } else if (this.showAllMeals && this.selectedCategory && this.filteredItems.length === 0) {
      itemsContent = KazzaUI.emptyState('🔍', 'Məhsul tapılmadı', 'Başqa kateqoriya seçin');
    } else if (!this.showAllMeals) {
      itemsContent = KazzaUI.emptyState('👆', 'Qrup seçin', 'Yuxarıdan yemək qrupunu seçin');
    } else if (!this.selectedCategory) {
      itemsContent = KazzaUI.emptyState('👆', 'Kateqoriya seçin', 'Yuxarıdan kateqoriya seçin');
    } else {
      itemsContent = this.filteredItems.map((item) => `
        <div class="menu-item ${this.loading ? 'disabled' : ''}" data-meal-id="${item.id}">
          <div class="menu-item-name">${item.name}</div>
          ${item.is_extra
            ? '<div class="menu-item-extra-badge">Extra</div>'
            : `<div class="menu-item-price">₼ ${item.price}</div>`}
        </div>
      `).join('');
    }

    panel.innerHTML = `
      <div class="menu">
        <div class="menu-nav">
          <div class="menu-tabs">${tabsHtml}</div>
          ${searchHtml}
        </div>
        <div class="menu-items-grid">${itemsContent}</div>
      </div>`;

    panel.querySelectorAll('[data-group-id]').forEach((el) => {
      el.addEventListener('click', () => {
        const group = this.mealGroups.find((g) => g.id === parseInt(el.dataset.groupId, 10));
        if (group) this.selectGroup(group);
      });
    });

    const backBtn = panel.querySelector('#back-to-groups');
    if (backBtn) backBtn.addEventListener('click', () => this.goBackToGroups());

    panel.querySelectorAll('[data-category-id]').forEach((el) => {
      el.addEventListener('click', () => {
        this.fetchMenuItems(parseInt(el.dataset.categoryId, 10));
      });
    });

    const search = panel.querySelector('#menu-search');
    if (search) {
      search.addEventListener('input', (e) => {
        this.searchQuery = e.target.value;
        this.render();
        const newSearch = document.getElementById('menu-search');
        if (newSearch) {
          newSearch.focus();
          newSearch.setSelectionRange(newSearch.value.length, newSearch.value.length);
        }
      });
    }

    panel.querySelectorAll('.menu-item').forEach((el) => {
      el.addEventListener('click', () => {
        const item = this.menuItems.find((m) => m.id === parseInt(el.dataset.mealId, 10));
        if (item) this.handleItemClick(item);
      });
    });
  },
};

window.MenuPanel = MenuPanel;
