// The reference photos open in a viewer on the page instead of leaving it. Without JavaScript
// each thumb is a plain link to the stored photo, and the original's page is linked under it.
// Keys: Escape closes, arrows move. Touch: swipe sideways to move. A click outside closes.

export function setupLightbox(root = document) {
  const box = root.querySelector('[data-lightbox]');
  const links = [...root.querySelectorAll('[data-photo]')];
  if (!box || !links.length || typeof box.showModal !== 'function') return null;
  const img = box.querySelector('[data-lb-img]');
  const caption = box.querySelector('[data-lb-caption]');
  const count = box.querySelector('[data-lb-count]');
  const author = box.querySelector('[data-lb-author]');
  const source = box.querySelector('[data-lb-source]');
  let at = 0;
  let opener = null;

  const photos = links.map((a) => {
    const fig = a.closest('figure');
    const src = fig.querySelector('[data-source]');
    return {
      full: a.getAttribute('href'),
      thumb: a.querySelector('img')?.currentSrc || a.querySelector('img')?.src || '',
      alt: a.querySelector('img')?.alt ?? '',
      caption: fig.querySelector('[data-caption]')?.textContent ?? '',
      author: src?.parentElement?.firstChild?.textContent?.replace(/\s*·\s*$/, '') ?? '',
      source: src ? { href: src.getAttribute('href'), text: src.textContent } : null,
    };
  });

  function warm(i) {
    const p = photos[(i + photos.length) % photos.length];
    if (p && !p.warm) { p.warm = new Image(); p.warm.src = p.full; }
  }

  function show(i) {
    at = (i + photos.length) % photos.length;
    const p = photos[at];
    box.classList.add('loading');
    // The thumb is already loaded: show it at once, sharpen when the full photo arrives.
    img.src = p.thumb || p.full;
    img.alt = p.alt;
    const full = new Image();
    full.onload = () => { if (photos[at] === p) { img.src = p.full; box.classList.remove('loading'); } };
    full.onerror = () => box.classList.remove('loading');
    full.src = p.full;
    caption.textContent = p.caption;
    count.textContent = `${at + 1} / ${photos.length}`;
    author.textContent = p.author;
    source.hidden = !p.source;
    if (p.source) { source.href = p.source.href; source.textContent = p.source.text; }
    warm(at + 1);
    warm(at - 1);
  }

  function open(i, from) {
    opener = from;
    show(i);
    box.showModal();
    document.documentElement.classList.add('lb-open');
  }

  links.forEach((a, i) => a.addEventListener('click', (ev) => {
    if (ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    ev.preventDefault();
    open(i, a);
  }));
  box.addEventListener('close', () => {
    document.documentElement.classList.remove('lb-open');
    img.removeAttribute('src');
    opener?.focus({ preventScroll: true });
  });
  box.querySelector('[data-lb-close]').addEventListener('click', () => box.close());
  box.querySelector('[data-lb-prev]').addEventListener('click', () => show(at - 1));
  box.querySelector('[data-lb-next]').addEventListener('click', () => show(at + 1));
  // A click on the backdrop (the dialog itself, outside the photo and buttons) closes it.
  box.addEventListener('click', (ev) => { if (ev.target === box) box.close(); });
  box.addEventListener('keydown', (ev) => {
    if (ev.key === 'ArrowLeft') { ev.preventDefault(); show(at - 1); }
    if (ev.key === 'ArrowRight') { ev.preventDefault(); show(at + 1); }
  });
  let x0 = null;
  box.addEventListener('pointerdown', (ev) => { if (ev.pointerType !== 'mouse') x0 = ev.clientX; });
  box.addEventListener('pointerup', (ev) => {
    if (x0 === null) return;
    const dx = ev.clientX - x0;
    x0 = null;
    if (Math.abs(dx) > 50) show(at + (dx < 0 ? 1 : -1));
  });
  return { open, show, get index() { return at; } };
}
