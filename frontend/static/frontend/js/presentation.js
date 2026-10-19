(function () {
  const links = [...document.querySelectorAll('.rail nav a[href^="#"]')];
  const sections = links
    .map((link) => document.querySelector(link.getAttribute('href')))
    .filter(Boolean);
  const rail = document.querySelector('.rail');
  const menuBtn = document.querySelector('.menu-btn');

  function setActive(id) {
    links.forEach((link) => {
      link.classList.toggle('active', link.getAttribute('href') === '#' + id);
    });
  }

  function currentId() {
    const line = 96;
    let current = sections[0];
    sections.forEach((section) => {
      if (section.getBoundingClientRect().top <= line) current = section;
    });
    return current.id;
  }

  function sync() { setActive(currentId()); }
  document.addEventListener('scroll', sync, { passive: true });
  sync();

  links.forEach((link) => {
    link.addEventListener('click', () => {
      setActive(link.getAttribute('href').slice(1));
      rail.classList.remove('open');
    });
  });
  if (menuBtn) {
    menuBtn.addEventListener('click', () => rail.classList.toggle('open'));
  }

  function indexOfCurrent() {
    return Math.max(0, sections.findIndex((section) => section.id === currentId()));
  }

  function go(step) {
    const next = sections[indexOfCurrent() + step];
    if (!next) return;
    next.scrollIntoView({ behavior: 'auto', block: 'start' });
    setActive(next.id);
  }

  document.getElementById('prev-section').addEventListener('click', () => go(-1));
  document.getElementById('next-section').addEventListener('click', () => go(1));

  document.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown' || event.key === 'PageDown') {
      event.preventDefault();
      go(1);
    }
    if (event.key === 'ArrowUp' || event.key === 'PageUp') {
      event.preventDefault();
      go(-1);
    }
  });
})();
