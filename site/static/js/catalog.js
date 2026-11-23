// The catalog page: cards lean towards the pointer. Pure enhancement; the page works without it.
import { mountAccount } from './account.js';

const still = matchMedia('(prefers-reduced-motion: reduce)').matches;

function tilt(card) {
  const link = card.querySelector('.card-link');
  if (!link) return;
  card.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse') return;
    const r = card.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    const y = (e.clientY - r.top) / r.height;
    card.style.setProperty('--mx', `${(x * 100).toFixed(1)}%`);
    card.style.setProperty('--my', `${(y * 100).toFixed(1)}%`);
    if (still) return;
    link.style.setProperty('--ry', `${((x - 0.5) * 10).toFixed(2)}deg`);
    link.style.setProperty('--rx', `${((0.5 - y) * 8).toFixed(2)}deg`);
  });
  card.addEventListener('pointerleave', () => {
    link.style.setProperty('--rx', '0deg');
    link.style.setProperty('--ry', '0deg');
    card.style.setProperty('--mx', '50%');
    card.style.setProperty('--my', '30%');
  });
}

for (const card of document.querySelectorAll('[data-card]')) tilt(card);
mountAccount();
document.body.dataset.ready = '1';
