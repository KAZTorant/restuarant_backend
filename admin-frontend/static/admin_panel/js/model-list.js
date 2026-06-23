const ModelList = {
  app: '',
  model: '',
  meta: null,
  page: 1,
  search: '',
  selected: new Set(),
  searchTimer: null,

  init(app, model) {
    this.app = app;
    this.model = model;
    this.bindEvents();
    this.load();
  },

  bindEvents() {
    document.getElementById('search-input')?.addEventListener('input', (e) => {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => {
        this.search = e.target.value;
        this.page = 1;
        this.loadList();
      }, 300);
    });
    document.getElementById('prev-page')?.addEventListener('click', () => {
      if (this.page > 1) { this.page -= 1; this.loadList(); }
    });
    document.getElementById('next-page')?.addEventListener('click', () => {
      this.page += 1;
      this.loadList();
    });
    document.getElementById('select-all')?.addEventListener('change', (e) => {
      document.querySelectorAll('.row-check').forEach((cb) => {
        cb.checked = e.target.checked;
        const id = Number(cb.dataset.id);
        if (e.target.checked) this.selected.add(id); else this.selected.delete(id);
      });
    });
  },

  async load() {
    try {
      await AdminUI.withLoading(async () => {
        this.meta = await AdminAPI.modelMeta(this.app, this.model);
        document.getElementById('page-title').textContent = this.meta.verbose_name_plural;
        this.renderActions();
        await this.loadList();
      });
    } catch (e) {
      document.getElementById('page-title').textContent = 'Xəta';
      AdminUI.handleApiError(e, 'Siyahı yüklənə bilmədi');
    }
  },

  renderActions() {
    const wrap = document.getElementById('toolbar-actions');
    if (!wrap) return;
    let html = '';
    if (this.meta.permissions.add) {
      html += `<a href="/panel/models/${this.app}/${this.model}/add/" class="btn btn-primary btn-sm">+ Əlavə et</a>`;
    }
    (this.meta.list.actions || []).forEach((a) => {
      html += `<button type="button" class="btn btn-secondary btn-sm action-btn" data-action="${a.name}">${AdminUI.escapeHtml(a.label)}</button>`;
    });
    wrap.innerHTML = html;
    wrap.querySelectorAll('.action-btn').forEach((btn) => {
      btn.addEventListener('click', () => this.runAction(btn.dataset.action));
    });
  },

  async loadList() {
    try {
      const params = { page: String(this.page) };
      if (this.search) params.q = this.search;
      const data = await AdminAPI.list(this.app, this.model, params);
      this.renderTable(data);
    } catch (e) {
      AdminUI.handleApiError(e, 'Siyahı yüklənə bilmədi');
    }
  },

  renderTable(data) {
    const cols = this.meta.list.columns;
    const thead = document.getElementById('table-head');
    const tbody = document.getElementById('table-body');
    thead.innerHTML = `<tr><th><input type="checkbox" id="select-all"></th>${cols.map((c) => `<th>${AdminUI.escapeHtml(c.label)}</th>`).join('')}<th></th></tr>`;
    document.getElementById('select-all')?.addEventListener('change', (e) => {
      this.selected.clear();
      document.querySelectorAll('.row-check').forEach((cb) => {
        cb.checked = e.target.checked;
        if (e.target.checked) this.selected.add(Number(cb.dataset.id));
      });
    });

    if (!data.results.length) {
      tbody.innerHTML = `<tr><td colspan="${cols.length + 2}" class="empty-state">Məlumat tapılmadı</td></tr>`;
    } else {
      tbody.innerHTML = data.results.map((row) => `
        <tr>
          <td><input type="checkbox" class="row-check" data-id="${row.id}"></td>
          ${cols.map((c) => `<td>${AdminUI.formatValue(row[c.name])}</td>`).join('')}
          <td>
            ${this.meta.permissions.change ? `<a href="/panel/models/${this.app}/${this.model}/${row.id}/change/" class="btn-link">Düzəliş</a>` : ''}
            ${this.meta.permissions.delete ? `<button type="button" class="btn-link danger delete-btn" data-id="${row.id}">Sil</button>` : ''}
          </td>
        </tr>`).join('');
      tbody.querySelectorAll('.row-check').forEach((cb) => {
        cb.addEventListener('change', () => {
          const id = Number(cb.dataset.id);
          if (cb.checked) this.selected.add(id); else this.selected.delete(id);
        });
      });
      tbody.querySelectorAll('.delete-btn').forEach((btn) => {
        btn.addEventListener('click', () => this.deleteRow(Number(btn.dataset.id)));
      });
    }

    document.getElementById('page-info').textContent = `Cəmi ${data.count} · Səhifə ${data.page}/${data.num_pages || 1}`;
    document.getElementById('prev-page').disabled = data.page <= 1;
    document.getElementById('next-page').disabled = data.page >= data.num_pages;
  },

  async deleteRow(id) {
    if (!AdminUI.confirm('Silmək istədiyinizə əminsiniz?')) return;
    await AdminUI.withLoading(() => AdminAPI.remove(this.app, this.model, id));
    AdminUI.toast('Silindi', 'success');
    this.loadList();
  },

  async runAction(name) {
    if (!this.selected.size) { AdminUI.toast('Heç nə seçilməyib', 'error'); return; }
    await AdminUI.withLoading(() => AdminAPI.action(this.app, this.model, name, [...this.selected]));
    AdminUI.toast('Əməliyyat tamamlandı', 'success');
    this.selected.clear();
    this.loadList();
  },
};

window.ModelList = ModelList;
