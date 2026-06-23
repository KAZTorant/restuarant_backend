document.addEventListener('dblclick', (e) => {
  e.preventDefault();
  e.stopPropagation();
}, { passive: false });

document.addEventListener('gesturestart', (e) => e.preventDefault());
