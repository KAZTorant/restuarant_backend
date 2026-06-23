const ModelForm = {
  app: '',
  model: '',
  pk: null,
  schema: null,
  data: {},

  init(app, model, pk) {
    this.app = app;
    this.model = model;
    this.pk = pk;
    document.getElementById('model-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submit();
    });
    this.load();
  },

  async load() {
    try {
      await AdminUI.withLoading(async () => {
        if (this.pk) {
          const res = await AdminAPI.detail(this.app, this.model, this.pk);
          this.schema = res.schema;
          this.data = res.object;
          document.getElementById('page-title').textContent = 'Düzəliş et';
        } else {
          const res = await AdminAPI.createSchema(this.app, this.model);
          this.schema = res.schema;
          this.data = {};
          document.getElementById('page-title').textContent = 'Yeni qeyd';
        }
        this.render();
      });
      await this.loadRelationChoices();
    } catch (e) {
      this.showLoadError(e);
    }
  },

  showLoadError(e) {
    document.getElementById('page-title').textContent = 'Xəta';
    const container = document.getElementById('form-fields');
    if (container) {
      container.innerHTML = `<div class="alert error">${AdminUI.escapeHtml(AdminUI.errorMessage(e, 'Form yüklənə bilmədi'))}</div>`;
    }
    AdminUI.handleApiError(e, 'Form yüklənə bilmədi');
  },

  render() {
    const container = document.getElementById('form-fields');
    const fieldNames = (this.schema.fields || []).map((f) => f.name);
    let groups = (this.schema.fieldsets || []).filter((g) => g.fields?.length);
    if (!groups.length && fieldNames.length) {
      groups = [{ title: '', fields: fieldNames }];
    }

    container.innerHTML = groups.map((g) => `
      <fieldset class="fieldset">
        ${g.title ? `<legend>${AdminUI.escapeHtml(g.title)}</legend>` : ''}
        <div class="form-grid">
          ${g.fields.map((name) => this.renderField(name)).join('')}
        </div>
      </fieldset>`).join('');

    if (!container.innerHTML.trim()) {
      container.innerHTML = '<div class="empty-state">Bu form üçün sahə tapılmadı</div>';
    }
  },

  async loadRelationChoices() {
    const selects = document.querySelectorAll('#form-fields select[data-fk]');
    await Promise.allSettled([...selects].map(async (select) => {
      const fk = select.dataset.fk;
      if (!fk || fk.includes('undefined')) return;

      const [app, model] = fk.split('/');
      if (!app || !model) return;

      try {
        const res = await AdminAPI.choices(app, model);
        const results = res.results || [];
        const isMultiple = select.multiple;
        const currentValues = isMultiple
          ? [...select.selectedOptions].map((o) => String(o.value))
          : [String(select.value)];

        select.innerHTML = [
          ...(isMultiple ? [] : ['<option value="">—</option>']),
          ...results.map((item) => {
            const selected = currentValues.includes(String(item.id)) ? ' selected' : '';
            return `<option value="${item.id}"${selected}>${AdminUI.escapeHtml(item.label)}</option>`;
          }),
        ].join('');
      } catch (e) {
        AdminUI.toast(`${fk} siyahısı yüklənmədi`, 'error');
      }
    }));
  },

  renderField(name) {
    const field = this.schema.fields.find((f) => f.name === name);
    if (!field) return '';
    const val = this.data[name];
    const id = `field-${name}`;
    let input = '';

    if (field.type === 'readonly' || field.type === 'computed') {
      input = `<div>${AdminUI.formatValue(val)}</div>`;
    } else if (field.type === 'boolean') {
      input = `<input type="checkbox" id="${id}" name="${name}" ${val ? 'checked' : ''}>`;
    } else if (field.choices?.length) {
      input = `<select id="${id}" name="${name}">${field.choices.map((c) => `<option value="${AdminUI.escapeHtml(c.value)}" ${String(val) === String(c.value) ? 'selected' : ''}>${AdminUI.escapeHtml(c.label)}</option>`).join('')}</select>`;
    } else if (field.type === 'foreign_key') {
      const cur = val && typeof val === 'object' ? val.id : val;
      const fk = field.related_model ? `${field.related_model.app_label}/${field.related_model.model_name}` : '';
      input = `<select id="${id}" name="${name}" data-fk="${fk}"><option value="">—</option>${cur ? `<option value="${cur}" selected>${AdminUI.escapeHtml(val?.label || cur)}</option>` : ''}</select>`;
    } else if (field.type === 'many_to_many') {
      const selected = Array.isArray(val) ? val.map((v) => String(v.id)) : [];
      const fk = field.related_model ? `${field.related_model.app_label}/${field.related_model.model_name}` : '';
      input = `<select id="${id}" name="${name}" multiple size="8" data-fk="${fk}" data-m2m="1">${selected.map((sid) => `<option value="${sid}" selected>${AdminUI.escapeHtml((val.find((v) => String(v.id) === sid) || {}).label || sid)}</option>`).join('')}</select>`;
    } else if (field.type === 'json') {
      input = `<textarea id="${id}" name="${name}">${AdminUI.escapeHtml(typeof val === 'object' ? JSON.stringify(val, null, 2) : (val ?? ''))}</textarea>`;
    } else if (field.type === 'text') {
      input = `<textarea id="${id}" name="${name}">${AdminUI.escapeHtml(val ?? '')}</textarea>`;
    } else if (field.type === 'date') {
      input = `<input type="date" id="${id}" name="${name}" value="${val ? String(val).slice(0, 10) : ''}">`;
    } else if (field.type === 'datetime') {
      input = `<input type="datetime-local" id="${id}" name="${name}" value="${val ? String(val).slice(0, 16) : ''}">`;
    } else if (field.type === 'password') {
      input = `<input type="password" id="${id}" name="${name}">`;
    } else if (field.type === 'file' || field.type === 'image') {
      input = `<input type="file" id="${id}" name="${name}">`;
    } else {
      input = `<input type="${field.type === 'integer' || field.type === 'decimal' ? 'number' : 'text'}" id="${id}" name="${name}" value="${AdminUI.escapeHtml(val ?? '')}" ${field.type === 'decimal' ? 'step="0.01"' : ''}>`;
    }

    return `<div class="form-group">
      <label for="${id}">${AdminUI.escapeHtml(field.label)}${field.required ? ' *' : ''}</label>
      ${input}
      ${field.help_text ? `<div class="help">${AdminUI.escapeHtml(field.help_text)}</div>` : ''}
    </div>`;
  },

  collectData() {
    const payload = {};
    this.schema.fields.forEach((field) => {
      if (field.type === 'readonly' || field.type === 'computed') return;
      const el = document.getElementById(`field-${field.name}`);
      if (!el) return;

      if (field.type === 'boolean') {
        payload[field.name] = el.checked;
      } else if (field.type === 'many_to_many') {
        payload[field.name] = [...el.selectedOptions].map((o) => o.value).filter(Boolean);
      } else if (field.type === 'json') {
        const raw = el.value.trim();
        if (raw) {
          payload[field.name] = JSON.parse(raw);
        }
      } else if (el.value !== '') {
        payload[field.name] = el.value;
      }
    });
    return payload;
  },

  async submit() {
    let payload;
    try {
      payload = this.collectData();
    } catch (e) {
      AdminUI.toast('JSON formatı səhvdir', 'error');
      return;
    }

    try {
      await AdminUI.withLoading(async () => {
        if (this.pk) {
          await AdminAPI.update(this.app, this.model, this.pk, payload);
        } else {
          const res = await AdminAPI.create(this.app, this.model, payload);
          window.location.href = `/panel/models/${this.app}/${this.model}/${res.id}/change/`;
          return;
        }
      });
      AdminUI.toast('Saxlanıldı', 'success');
    } catch (e) {
      AdminUI.handleApiError(e, 'Saxlama uğursuz oldu');
    }
  },
};

window.ModelForm = ModelForm;
