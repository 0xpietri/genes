// Where the species lives, drawn as a toy map: land and sea from Natural Earth, the main
// rivers, the big peaks of the Andes and the Sierras as painted mountains, and a little
// painted algarrobo wherever it has been seen (GBIF sightings per half-degree area once
// fetched; until then, where the reference photos were taken). Drag to move, wheel, pinch or
// the buttons to zoom. SVG only, no tiles.

import { t } from './i18n.js';

const NS = 'http://www.w3.org/2000/svg';
const ASPECT = 4 / 3;

function svg(tag, attrs = {}, parent = null) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.append(node);
  return node;
}

// Peaks drawn as painted mountains (decoration only): [lon, lat, piece].
const PEAKS = [
  [-70.01, -32.65, 'mountain-snow'], // Aconcagua
  [-68.54, -27.11, 'mountain-snow'], // Ojos del Salado
  [-68.54, -24.72, 'mountain-snow'], // Llullaillaco
  [-66.95, -16.27, 'mountain-snow'], // Cordillera Real, Bolivia
  [-64.94, -31.99, 'mountain-rock'], // Champaquí, Sierras de Córdoba
  [-66.05, -27.0, 'mountain-rock'], // Aconquija
];

// Sea and land colours, and a drawn tree for when the painted pieces are missing.
const DEFS = `
<linearGradient id="map-sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8fd0e6"/><stop offset="1" stop-color="#6bb8d6"/></linearGradient>
<linearGradient id="map-land" x1="0" y1="0" x2="0.4" y2="1"><stop offset="0" stop-color="#bcd98f"/><stop offset=".55" stop-color="#cfd98e"/><stop offset="1" stop-color="#e0cf95"/></linearGradient>
<g id="map-tree">
  <ellipse cx="0" cy="0" rx="9" ry="2.6" fill="#1d2a26" opacity=".25"/>
  <path d="M-1.6 0 L-1 -11 L1 -11 L1.6 0Z" fill="#8a5a3b" stroke="#1d2a26" stroke-width="1.3" stroke-linejoin="round"/>
  <path d="M-11 -11c0-6 4-11 11-11s11 5 11 11c-4 2-18 2-22 0Z" fill="#a9c98c" stroke="#1d2a26" stroke-width="1.3" stroke-linejoin="round"/>
  <path d="M-6 -16c2-2 5-3 8-3" fill="none" stroke="#e4f2c9" stroke-width="1.6" stroke-linecap="round"/>
</g>`;

/** A painted piece as a symbol standing on (0, 0), `tall` units high, with a soft shadow. */
function pieceSymbol(defs, art, name, tall, shadow) {
  const size = art.sizes?.[name];
  if (!size) return null;
  const w = (tall * size[0]) / size[1];
  const g = svg('g', { id: `map-${name}` }, defs);
  if (shadow) svg('ellipse', { cx: 0, cy: -0.5, rx: w * 0.3, ry: tall * 0.08, fill: '#1d2a26', opacity: '.22' }, g);
  svg('image', { href: `${art.url}/${name}.webp`, x: -w / 2, y: -tall, width: w, height: tall }, g);
  return `#map-${name}`;
}

export async function startMap(figure) {
  const holder = figure.querySelector('[data-map-canvas]');
  const points = JSON.parse(figure.dataset.points || '{}');
  const art = JSON.parse(figure.dataset.art || '{}');
  let base;
  try {
    const res = await fetch(figure.dataset.basemap);
    base = await res.json();
  } catch {
    holder.querySelector('.map-wait').textContent = t('The map could not load.');
    return;
  }
  const project = (lon, lat) => [(lon - base.box[0]) * base.unit * base.cos, (base.box[3] - lat) * base.unit];

  const root = svg('svg', { viewBox: `0 0 ${base.width} ${base.height}`, role: 'img', 'aria-label': t('Map of where the species grows') });
  const defs = svg('defs', {}, root);
  defs.innerHTML = DEFS;
  const trees = [1, 2, 3, 4, 5, 6].map((k) => pieceSymbol(defs, art, `tree-${k}`, 26, true)).filter(Boolean);
  const peaks = {};
  for (const name of ['mountain-snow', 'mountain-rock']) peaks[name] = pieceSymbol(defs, art, name, 30, false);
  svg('rect', { x: -base.width, y: -base.height, width: base.width * 3, height: base.height * 3, class: 'sea' }, root);
  const land = svg('g', {}, root);
  const all = base.countries.map((c) => c.d).join('');
  svg('path', { d: all, class: 'shore' }, land);
  svg('path', { d: all, class: 'land' }, land);
  for (const c of base.countries) svg('path', { d: c.d, class: 'border' }, land);
  for (const l of base.lakes ?? []) svg('path', { d: l.d, class: 'lake' }, land);
  const rivers = [];
  for (const r of base.rivers ?? []) {
    const path = svg('path', { d: r.d, class: 'river' }, land);
    rivers.push({ path, w: Math.max(0.8, 3.2 - r.rank * 0.4) });
  }

  // Mountains, then marks: GBIF areas when there are any, else the photos' places.
  const pins = [];
  const deco = svg('g', { 'aria-hidden': 'true' }, root);
  for (const [lon, lat, name] of [...PEAKS].sort((a, b) => b[1] - a[1])) {
    if (!peaks[name]) continue;
    const [x, y] = project(lon, lat);
    const g = svg('g', { class: 'peak' }, deco);
    svg('use', { href: peaks[name] }, g);
    pins.push({ g, text: null, x, y, size: 1, deco: true });
  }
  const marks = svg('g', {}, root);
  const cells = points.cells ?? [];
  const tip = document.createElement('div');
  tip.className = 'map-tip';
  tip.hidden = true;
  let nTree = 0;
  const addPin = (lon, lat, size, label, symbol = null, name = null) => {
    const [x, y] = project(lon, lat);
    symbol ??= trees.length ? trees[(nTree++ * 7 + Math.round(Math.abs(lon * 13 + lat * 7))) % trees.length] : '#map-tree';
    const g = svg('g', { class: 'pin', tabindex: '0', 'aria-label': label }, marks);
    svg('use', { href: symbol }, g);
    const show = () => {
      const r = holder.getBoundingClientRect();
      const b = g.getBoundingClientRect();
      tip.textContent = label;
      tip.style.left = `${b.left + b.width / 2 - r.left}px`;
      tip.style.top = `${b.top - r.top}px`;
      tip.hidden = false;
    };
    g.addEventListener('pointerenter', show);
    g.addEventListener('focus', show);
    g.addEventListener('pointerleave', () => { tip.hidden = true; });
    g.addEventListener('blur', () => { tip.hidden = true; });
    let text = null;
    if (name) {
      text = svg('text', { class: 'label' }, marks);
      text.textContent = name;
    }
    pins.push({ g, text, x, y, size });
  };
  if (cells.length) {
    const max = Math.max(...cells.map((c) => c[2]));
    // South first, so trees further north stand behind.
    for (const [lon, lat, n] of [...cells].sort((a, b) => b[1] - a[1])) {
      addPin(lon, lat, 0.55 + 0.6 * Math.sqrt(n / max), `${n} ${t(n === 1 ? 'sighting here' : 'sightings here')}`);
    }
  } else {
    for (const p of points.places ?? []) {
      const n = p.photos.length;
      addPin(p.lon, p.lat, 0.8 + Math.min(0.6, Math.sqrt(n) * 0.18), `${p.name}: ${n} ${t(n === 1 ? 'reference photo' : 'reference photos')}`);
    }
  }

  holder.replaceChildren(root, tip);

  // ---- view box: start on the marks, drag to pan, zoom around the pointer
  const xy = pins.filter((p) => !p.deco).map((p) => [p.x, p.y]);
  const xs = xy.map((p) => p[0]);
  const ys = xy.map((p) => p[1]);
  const home = xy.length
    ? (() => {
      const pad = 45;
      const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad, y0 = Math.min(...ys) - pad * 1.4, y1 = Math.max(...ys) + pad;
      const w = Math.max(x1 - x0, (y1 - y0) * ASPECT, 140);
      const h = w / ASPECT;
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      return { x: cx - w / 2, y: cy - h / 2, w, h };
    })()
    : { x: 0, y: 0, w: base.width, h: base.width / ASPECT };
  let vb = { ...home };
  function draw() {
    root.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    const px = vb.w / Math.max(1, holder.clientWidth); // view units per screen pixel
    const k = px * 1.15;
    for (const p of pins) {
      p.g.setAttribute('transform', `translate(${p.x.toFixed(2)} ${p.y.toFixed(2)}) scale(${(k * p.size).toFixed(4)})`);
      if (p.text) {
        p.text.setAttribute('x', (p.x + 14 * px).toFixed(2));
        p.text.setAttribute('y', (p.y - 4 * px).toFixed(2));
        p.text.style.fontSize = `${13 * px}px`;
      }
    }
    for (const r of rivers) r.path.style.strokeWidth = `${r.w}px`;
  }
  function zoom(factor, cx = vb.x + vb.w / 2, cy = vb.y + vb.h / 2) {
    const w = Math.min(base.width * 1.2, Math.max(20, vb.w * factor));
    const k = w / vb.w;
    vb = { x: cx - (cx - vb.x) * k, y: cy - (cy - vb.y) * k, w, h: vb.h * k };
    draw();
  }
  const toView = (e) => {
    const r = holder.getBoundingClientRect();
    return [vb.x + ((e.clientX - r.left) / r.width) * vb.w, vb.y + ((e.clientY - r.top) / r.height) * vb.h];
  };
  holder.addEventListener('wheel', (e) => { e.preventDefault(); const [x, y] = toView(e); zoom(e.deltaY > 0 ? 1.2 : 1 / 1.2, x, y); }, { passive: false });
  const pointers = new Map();
  let pinch = 0;
  holder.addEventListener('pointerdown', (e) => { holder.setPointerCapture(e.pointerId); pointers.set(e.pointerId, { x: e.clientX, y: e.clientY }); });
  holder.addEventListener('pointermove', (e) => {
    const prev = pointers.get(e.pointerId);
    if (!prev) return;
    const r = holder.getBoundingClientRect();
    if (pointers.size === 1) {
      vb.x -= ((e.clientX - prev.x) / r.width) * vb.w;
      vb.y -= ((e.clientY - prev.y) / r.height) * vb.h;
      draw();
    }
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch) zoom(pinch / d, ...toView({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 }));
      pinch = d;
    }
  });
  const up = (e) => { pointers.delete(e.pointerId); if (pointers.size < 2) pinch = 0; };
  holder.addEventListener('pointerup', up);
  holder.addEventListener('pointercancel', up);
  for (const b of figure.querySelectorAll('[data-zoom]')) {
    b.addEventListener('click', () => {
      const z = Number(b.dataset.zoom);
      if (z === 0) { vb = { ...home }; draw(); } else zoom(z > 0 ? 1 / 1.5 : 1.5);
    });
  }
  new ResizeObserver(draw).observe(holder);
  draw();
}
