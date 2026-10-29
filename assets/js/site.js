// Mobile nav toggle
(() => {
  const btn = document.querySelector('.nav-toggle');
  const nav = document.getElementById('site-nav');
  if (!btn || !nav) return;
  btn.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    btn.setAttribute('aria-expanded', String(open));
  });
})();

// Theme: light / dark / system. The choice is stored; "system" clears it.
(() => {
  const root = document.documentElement;
  const buttons = [...document.querySelectorAll('[data-theme-choice]')];
  const read = () => { try { return localStorage.getItem('theme') || 'system'; } catch (e) { return 'system'; } };
  const apply = (choice) => {
    if (choice === 'light' || choice === 'dark') root.setAttribute('data-theme', choice);
    else root.removeAttribute('data-theme');
    buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.themeChoice === choice)));
  };
  buttons.forEach(b => b.addEventListener('click', () => {
    const choice = b.dataset.themeChoice;
    try { choice === 'system' ? localStorage.removeItem('theme') : localStorage.setItem('theme', choice); } catch (e) {}
    apply(choice);
  }));
  apply(read());
})();

// Chapters: jump the YouTube embed or audio player to a timestamp
(() => {
  const entry = document.querySelector('[data-entry]');
  if (!entry) return;
  entry.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-seek]');
    if (!btn) return;
    const t = Number(btn.dataset.seek) || 0;
    const audio = entry.querySelector('audio[data-player]');
    const frame = entry.querySelector('iframe[data-player="youtube"]');
    if (audio) {
      audio.currentTime = t;
      audio.play();
    } else if (frame) {
      const url = new URL(frame.src);
      url.searchParams.set('start', String(t));
      url.searchParams.set('autoplay', '1');
      frame.src = url.toString();
      frame.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    entry.querySelectorAll('[data-seek]').forEach(b => b.removeAttribute('aria-current'));
    btn.setAttribute('aria-current', 'true');
  });
})();

// Lightbox: links with data-lightbox open their image in a modal.
// Click the image to switch between fit-to-screen and full size.
(() => {
  const dialog = document.querySelector('[data-lightbox-dialog]');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const img = dialog.querySelector('[data-lightbox-img]');
  const stage = dialog.querySelector('[data-lightbox-stage]');
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a[data-lightbox]');
    if (!link) return;
    e.preventDefault();
    const thumb = link.querySelector('img');
    img.src = link.href;
    img.alt = thumb ? thumb.alt : '';
    dialog.classList.remove('is-zoomed');
    dialog.showModal();
  });
  img.addEventListener('click', (e) => {
    const zoomed = dialog.classList.toggle('is-zoomed');
    if (zoomed) {
      // Keep the clicked spot under the cursor
      const r = img.getBoundingClientRect();
      const fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
      requestAnimationFrame(() => {
        stage.scrollLeft = img.scrollWidth * fx - stage.clientWidth / 2;
        stage.scrollTop = img.scrollHeight * fy - stage.clientHeight / 2;
      });
    }
  });
  dialog.querySelector('[data-lightbox-close]').addEventListener('click', () => dialog.close());
  // Click on the backdrop (outside the stage) closes
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });
})();
