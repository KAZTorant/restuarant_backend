const AdminAPI = {
  base: '/admin-api',

  async request(method, path, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'include',
    };
    if (body !== null && method !== 'GET') {
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(`${this.base}${path}`, opts);
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.detail || `HTTP ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  },

  get(path) { return this.request('GET', path); },
  post(path, body) { return this.request('POST', path, body); },
  patch(path, body) { return this.request('PATCH', path, body); },
  delete(path) { return this.request('DELETE', path); },

  login(username, password) {
    return this.post('/auth/login/', { username, password });
  },
  logout() { return this.post('/auth/logout/', {}); },
  me() { return this.get('/auth/me/'); },
  navigation() { return this.get('/navigation/'); },

  modelMeta(app, model) { return this.get(`/${app}/${model}/meta/`); },
  list(app, model, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.get(`/${app}/${model}/${qs ? `?${qs}` : ''}`);
  },
  detail(app, model, pk) { return this.get(`/${app}/${model}/${pk}/`); },
  createSchema(app, model) { return this.get(`/${app}/${model}/create/`); },
  create(app, model, data) { return this.post(`/${app}/${model}/create/`, data); },
  update(app, model, pk, data) { return this.patch(`/${app}/${model}/${pk}/`, data); },
  remove(app, model, pk) { return this.delete(`/${app}/${model}/${pk}/`); },
  choices(app, model, q = '') {
    return this.get(`/${app}/${model}/choices/${q ? `?q=${encodeURIComponent(q)}` : ''}`);
  },
  action(app, model, actionName, ids) {
    return this.post(`/${app}/${model}/actions/${actionName}/`, { ids });
  },

  statistics: {
    get(action) { return AdminAPI.get(`/custom/statistics/${action}/`); },
    post(action, data = {}) { return AdminAPI.post(`/custom/statistics/${action}/`, data); },
  },
  summary: {
    create(start, end) { return AdminAPI.post('/custom/summary/create-summary/', { start_date: start, end_date: end }); },
    preview(id) { return AdminAPI.get(`/custom/summary/preview-summary/${id}/`); },
  },
  paymentCalc: {
    calculate(data) { return AdminAPI.post('/custom/payment-calculation/calculate/', data); },
  },
  withdrawn: {
    total(start, end) { return AdminAPI.post('/custom/withdrawn-list/calculate-total/', { start_date: start, end_date: end }); },
  },
};

window.AdminAPI = AdminAPI;
