(function () {
  const form = document.getElementById('login-form');
  const input = document.getElementById('pin-input');
  const dots = document.querySelectorAll('.pin-dot');
  const dotsContainer = document.getElementById('pin-dots');
  const submitBtn = document.getElementById('submit-btn');
  if (!form || !input || !submitBtn) return;

  const submitLabel = submitBtn.textContent;
  let pin = '';
  let submitting = false;
  let submitTimer = null;

  function updateDisplay() {
    dots.forEach((dot, i) => {
      dot.classList.toggle('filled', i < pin.length);
    });
    input.value = pin;
    dotsContainer.classList.toggle('active', pin.length > 0);
  }

  function resetLogin() {
    submitting = false;
    pin = '';
    updateDisplay();
    submitBtn.classList.remove('loading');
    submitBtn.textContent = submitLabel;
    if (window.KazzaUI) KazzaUI.forceHideLoading();
    if (submitTimer) {
      clearTimeout(submitTimer);
      submitTimer = null;
    }
  }

  function submitPin() {
    if (submitting || pin.length !== 4) return;
    submitting = true;
    submitBtn.classList.add('loading');
    submitBtn.textContent = 'Gözləyin...';
    if (window.KazzaUI) KazzaUI.showLoading('Daxil olunur...');
    submitTimer = setTimeout(() => {
      resetLogin();
      if (window.KazzaUI) {
        KazzaUI.error('Giriş cavabı gəlmədi. Şəbəkəni yoxlayıb yenidən cəhd edin.');
      }
    }, 12000);
    HTMLFormElement.prototype.submit.call(form);
  }

  function pressKey(key) {
    if (submitting || pin.length >= 4) return;
    pin += key;
    updateDisplay();
    if (pin.length === 4) submitPin();
  }

  document.querySelectorAll('.keypad .number').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      pressKey(btn.dataset.key);
    });
  });

  document.getElementById('clear-btn').addEventListener('click', (event) => {
    event.preventDefault();
    if (submitting) return;
    pin = '';
    updateDisplay();
  });

  window.addEventListener('pageshow', resetLogin);

  window.kazzaRenderQr = function renderQr() {
    const el = document.getElementById('qr-code');
    if (!el || el.dataset.ready || !window.KAZZA_QR_URL || typeof QRCode === 'undefined') return;
    el.dataset.ready = '1';
    new QRCode(el, {
      text: window.KAZZA_QR_URL,
      width: 180,
      height: 180,
      colorDark: '#0f172a',
      colorLight: '#ffffff',
    });
  };

  document.addEventListener('DOMContentLoaded', window.kazzaRenderQr);
})();
