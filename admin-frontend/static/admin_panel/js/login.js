document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('login-form');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errEl = document.getElementById('login-error');
    errEl.classList.add('hidden');
    try {
      await AdminUI.withLoading(() => AdminAPI.login(username, password));
      window.location.href = '/panel/';
    } catch (err) {
      errEl.textContent = err.message || 'Giriş uğursuz';
      errEl.classList.remove('hidden');
    }
  });
});
