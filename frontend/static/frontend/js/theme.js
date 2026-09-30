(function () {
  const storageKey = 'kazza-theme';

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function paintButtons(theme) {
    const isDark = theme === 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.textContent = isDark ? 'Light' : 'Dark';
      button.setAttribute('aria-pressed', isDark ? 'true' : 'false');
      button.setAttribute('aria-label', isDark ? 'Light mode' : 'Dark mode');
    });
  }

  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    try {
      localStorage.setItem(storageKey, theme);
    } catch (e) {}
    paintButtons(theme);
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-theme-toggle]');
    if (!button) return;
    applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
  });

  paintButtons(currentTheme());
})();
