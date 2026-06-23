document.addEventListener('DOMContentLoaded', async () => {
  document.getElementById('btn-calc-withdrawn')?.addEventListener('click', async () => {
    const start = document.getElementById('w-start').value;
    const end = document.getElementById('w-end').value;
    try {
      const res = await AdminUI.withLoading(() => AdminAPI.withdrawn.total(start, end));
      document.getElementById('w-result').textContent = `${res.total_withdrawn} AZN (${res.count} qeyd)`;
    } catch (e) { AdminUI.toast(e.message, 'error'); }
  });
  ModelList.init('orders', 'withdrawnlist');
});
