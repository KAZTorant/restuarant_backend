(function () {
  const form = document.getElementById('login-form');
  const input = document.getElementById('pin-input');
  const dots = document.querySelectorAll('.pin-dot');
  const dotsContainer = document.getElementById('pin-dots');
  const submitBtn = document.getElementById('submit-btn');
  let pin = '';

  function updateDisplay() {
    dots.forEach((dot, i) => {
      dot.classList.toggle('filled', i < pin.length);
    });
    input.value = pin;
    dotsContainer.classList.toggle('active', pin.length > 0);
  }

  document.querySelectorAll('.keypad .number').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (pin.length < 4) {
        pin += btn.dataset.key;
        updateDisplay();
        if (pin.length === 4) {
          submitBtn.classList.add('loading');
          submitBtn.textContent = 'Gözləyin...';
          KazzaUI.showLoading('Daxil olunur...');
          form.submit();
        }
      }
    });
  });

  document.getElementById('clear-btn').addEventListener('click', () => {
    pin = '';
    updateDisplay();
  });

  if (window.KAZZA_QR_URL && typeof QRCode !== 'undefined') {
    new QRCode(document.getElementById('qr-code'), {
      text: window.KAZZA_QR_URL,
      width: 180,
      height: 180,
      colorDark: '#0f172a',
      colorLight: '#ffffff',
    });
  }
})();
