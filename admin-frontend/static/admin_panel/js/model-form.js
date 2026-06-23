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
      await this.loadForeignKeyChoices();
    });
  },

  render() {
    const container = document.getElementById('form-fields');
    const groups = this.schema.fieldsets.length ? this.schema.fieldsets : [{
      title: '', fields: this.schema.fields.map((f) => f.name),
    }];

    container.innerHTML = groups.map((g) => `
      <fieldset class="fieldset">
        ${g.title ? `<legend>${AdminUI.escapeHtml(g.title)}</legend>` : ''}
        <div class="form-grid">
          ${g.fields.map((name) => this.renderField(name)).join('')}
        </div>
      </fieldset>`).join('');
  },

  async loadForeignKeyChoices() {
    const selects = document.querySelectorAll('#form-fields select[data-fk]');
    await Promise.all([...selects].map(async (select) => {
      const [app, model] = select.dataset.fk.split('/');
      const res = await AdminAPI.choices(app, model);
      const current = select.value;
      select.innerHTML = [
        '<option value="">—</option>',
        ...res.results.map((item) => (
          `<option value="${item.id}" ${String(item.id) === String(current) ? 'selected' : ''}>${AdminUI.escapeHtml(item.label)}</option>`
        )),
      ].join('');
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
      input = `<select id="${id}" name="${name}" data-fk="${field.related_model?.app_label}/${field.related_model?.model_name}"><option value="">—</option>${cur ? `<option value="${cur}" selected>${AdminUI.escapeHtml(val?.label || cur)}</option>` : ''}</select>`;
    } else if (field.type === 'text') {
      input = `<textarea id="${id}" name="${name}">${AdminUI.escapeHtml(val ?? '')}</textarea>`;
    } else if (field.type === 'date') {
      input = `<input type="date" id="${id}" name="${name}" value="${val ? String(val).slice(0, 10) : ''}">`;
    } else if (field.type === 'datetime') {
      input = `<input type="datetime-local" id="${id}" name="${name}" value="${val ? String(val).slice(0, 16) : ''}">`;
    } else if (field.type === 'password') {
      input = `<input type="password" id="${id}" name="${name}">`;
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
      if (field.type === 'boolean') payload[field.name] = el.checked;
      else if (el.value !== '') payload[field.name] = el.value;
    });
    return payload;
  },

  async submit() {
    const payload = this.collectData();
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
      if (e.data?.errors) {
        AdminUI.toast(Object.values(e.data.errors).flat().join(', '), 'error');
      } else {
        AdminUI.toast(e.message, 'error');
      }
    }
  },
};

window.ModelForm = ModelForm;
