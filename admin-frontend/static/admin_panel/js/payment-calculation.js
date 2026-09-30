document.addEventListener('DOMContentLoaded', () => {
  ModelList.init('payments', 'paymentcalculation');

  document.getElementById('btn-calculate')?.addEventListener('click', async () => {
    const today = new Date().toISOString().slice(0, 10);
    let restaurantHtml = '';
    try {
      const me = await AdminAPI.me();
      if (!me.is_superuser && !me.restaurant) {
        AdminUI.toast('Hesabınıza restoran təyin edilməyib.', 'error');
        return;
      }
      if (me.restaurant) {
        restaurantHtml = `
          <div class="form-group">
            <label>Restoran</label>
            <input type="text" value="${AdminUI.escapeHtml(me.restaurant.name)}" disabled>
            <input type="hidden" id="c-restaurant" value="${me.restaurant.id}">
          </div>`;
      } else {
        const data = await AdminAPI.choices('tenants', 'restaurant');
        const options = (data.results || []).map((r) => {
          const selected = me.restaurant && String(me.restaurant.id) === String(r.id) ? ' selected' : '';
          return `<option value="${r.id}"${selected}>${AdminUI.escapeHtml(r.label)}</option>`;
        }).join('');
        restaurantHtml = `
          <div class="form-group">
            <label>Restoran</label>
            <select id="c-restaurant" required>
              <option value="">Restoran seçin</option>
              ${options}
            </select>
          </div>`;
      }
    } catch (e) {
      AdminUI.toast(e.message, 'error');
      return;
    }

    const modal = AdminUI.openModal('Ödəniş Hesablaması', `
      <div class="form-grid">
        ${restaurantHtml}
        <div class="form-group"><label>Başlanğıc tarixi</label><input type="date" id="c-start" value="${today}"></div>
        <div class="form-group"><label>Bitiş tarixi</label><input type="date" id="c-end" value="${today}"></div>
        <div class="form-group"><label>Başlanğıc saatı</label><input type="text" id="c-stime" value="12:00"></div>
        <div class="form-group"><label>Bitiş saatı</label><input type="text" id="c-etime" value="23:59"></div>
      </div>
      <button class="btn btn-primary" id="c-submit">Hesabla</button>`, true);
    modal.querySelector('#c-submit').onclick = async () => {
      const restaurantId = modal.querySelector('#c-restaurant')?.value;
      if (!restaurantId) {
        AdminUI.toast('Restoran seçin.', 'error');
        return;
      }
      try {
        const res = await AdminUI.withLoading(() => AdminAPI.paymentCalc.calculate({
          restaurant: restaurantId,
          start_date: modal.querySelector('#c-start').value,
          end_date: modal.querySelector('#c-end').value,
          start_time: modal.querySelector('#c-stime').value,
          end_time: modal.querySelector('#c-etime').value,
        }));
        modal.querySelector('.modal-body').innerHTML = `
          <div class="alert success">${AdminUI.escapeHtml(res.detail)}</div>
          <div class="stats-grid">
            <div class="stat-card"><div class="label">Cəmi</div><div class="value">${res.total_amount} AZN</div></div>
            <div class="stat-card"><div class="label">Ödəniş sayı</div><div class="value">${res.payment_count}</div></div>
          </div>
          <a href="/panel/models/payments/paymentcalculation/${res.id}/change/" class="btn btn-primary">Detallı bax</a>`;
        ModelList.loadList();
      } catch (e) { AdminUI.toast(e.message, 'error'); }
    };
  });
});
