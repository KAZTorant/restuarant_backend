document.addEventListener('DOMContentLoaded', async () => {
  await StatisticsPage.init();
  ModelList.init('orders', 'summary');

  document.getElementById('btn-create-summary')?.addEventListener('click', () => {
    const modal = AdminUI.openModal('Tarix Aralığı Hesabatı', `
      <div class="form-group"><label>Başlanğıc</label><input type="date" id="s-start"></div>
      <div class="form-group"><label>Bitiş</label><input type="date" id="s-end"></div>
      <button class="btn btn-primary" id="s-submit">Yarat</button>`);
    modal.querySelector('#s-submit').onclick = async () => {
      try {
        const res = await AdminUI.withLoading(() => AdminAPI.summary.create(
          modal.querySelector('#s-start').value,
          modal.querySelector('#s-end').value,
        ));
        AdminUI.toast(res.detail || 'Yaradıldı', 'success');
        modal.remove();
        window.location.href = `/panel/models/orders/summary/${res.id}/change/`;
      } catch (e) { AdminUI.toast(e.message, 'error'); }
    };
  });
});
