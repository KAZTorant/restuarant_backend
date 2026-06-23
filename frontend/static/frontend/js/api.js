const KazzaAPI = {
  pin: '',

  init(pin) {
    this.pin = pin;
  },

  headers() {
    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-PIN': this.pin,
    };
  },

  async request(method, url, body = null) {
    const options = { method, headers: this.headers() };
    if (body !== null && method !== 'GET') {
      options.body = JSON.stringify(body);
    }
    const response = await fetch(url, options);
    if (!response.ok) {
      const err = new Error(`HTTP ${response.status}`);
      err.response = response;
      try { err.data = await response.json(); } catch (_) {}
      throw err;
    }
    if (response.status === 204) return null;
    const text = await response.text();
    return text ? JSON.parse(text) : null;
  },

  get(url) { return this.request('GET', url); },
  post(url, body) { return this.request('POST', url, body); },
  delete(url, body) { return this.request('DELETE', url, body); },

  login(pin) {
    return this.post('/api/users/login/', { pin });
  },

  fetchRooms() { return this.get('/api/tables/rooms/'); },
  fetchTablesByHallId(id) { return this.get(`/api/tables/${id}/tables/`); },
  fetchTableDetails(tableId) { return this.get(`/api/tables/${tableId}/details`); },

  createOrder(tableId) { return this.post(`/api/orders/${tableId}/create/`, {}); },
  listOrders(tableId) { return this.get(`/api/orders/${tableId}/list-orders/`); },
  listOrderItems(tableId, orderId) {
    return this.get(`/api/orders/${tableId}/list-order-items/?order_id=${orderId}`);
  },

  addOrderItem(tableId, mealId, quantity, orderId, description = null, price = null) {
    return this.post(`/api/orders/${tableId}/add-order-item/`, {
      meal_id: mealId, quantity, order_id: orderId,
      description, price,
    });
  },

  deleteOrderItem(tableId, data) {
    return this.delete(`/api/orders/${tableId}/delete-order-item/`, data);
  },

  commentOrderItem(tableId, mealId, comment, orderId) {
    return this.post(`/api/orders/${tableId}/comment/`, {
      meal_id: mealId, comment, order_id: orderId,
    });
  },

  transferOrderItems(tableId, data) {
    return this.post(`/api/orders/${tableId}/tranfer-order-items/`, data);
  },

  changeTableForOrder(oldTableId, newTableId) {
    return this.post(`/api/orders/${oldTableId}/change-table-for-order/`, {
      new_table_id: newTableId,
    });
  },

  changeWaitressForOrder(tableId, newWaitressId) {
    return this.post(`/api/orders/${tableId}/change-waitress/`, {
      new_waitress_id: newWaitressId,
    });
  },

  fetchWaitresses() { return this.get('/api/orders/list-waitress/'); },
  printCheck(tableId) { return this.post(`/api/orders/${tableId}/print-check/`, {}); },
  deleteCheck(tableId) { return this.request('DELETE', `/api/orders/${tableId}/print-check/`); },
  combineTables(tableId, otherTableIds) {
    return this.post(`/api/orders/${tableId}/join-tables-orders/`, {
      other_table_ids: otherTableIds,
    });
  },

  cancelPayment(tableId, payload) {
    return this.post(`/api/payments/${tableId}/pay-orders/`, payload);
  },

  fetchMealGroups() { return this.get('/api/meals/groups/'); },
  fetchMealsByCategoryId(categoryId) {
    const url = categoryId
      ? `/api/meals/meals/?meal_category_id=${categoryId}`
      : '/api/meals/meals/';
    return this.get(url);
  },

  confirmOrder(tableId, orderId = null) {
    const body = orderId ? { order_id: orderId } : {};
    return this.post(`/api/orders/${tableId}/confirm/`, body);
  },
};

window.KazzaAPI = KazzaAPI;
