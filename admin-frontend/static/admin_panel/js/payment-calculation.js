document.addEventListener('DOMContentLoaded', () => {
  ModelList.init('payments', 'paymentcalculation');

  document.getElementById('btn-calculate')?.addEventListener('click', () => {
    const today = new Date().toISOString().slice(0, 10);
    const modal = AdminUI.openModal('Ödəniş Hesablaması', `
      <div class="form-grid">
        <div class="form-group"><label>Başlanğıc tarixi</label><input type="date" id="c-start" value="${today}"></div>
        <div class="form-group"><label>Bitiş tarixi</label><input type="date" id="c-end" value="${today}"></div>
        <div class="form-group"><label>Başlanğıc saatı</label><input type="text" id="c-stime" value="12:00"></div>
        <div class="form-group"><label>Bitiş saatı</label><input type="text" id="c-etime" value="23:59"></div>
      </div>
      <button class="btn btn-primary" id="c-submit">Hesabla</button>`, true);
    modal.querySelector('#c-submit').onclick = async () => {
      try {
        const res = await AdminUI.withLoading(() => AdminAPI.paymentCalc.calculate({
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
