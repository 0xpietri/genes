// Where the species lives, drawn as a toy map: land and sea from Natural Earth, the main
// rivers, and a little algarrobo wherever it has been seen (GBIF sightings per half-degree
// area once fetched; until then, where the reference photos were taken). A house marks
// Unquillo. Drag to move, wheel, pinch or the buttons to zoom. SVG only, no tiles.

const NS = 'http://www.w3.org/2000/svg';
const ASPECT = 4 / 3;

function svg(tag, attrs = {}, parent = null) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.append(node);
  return node;
}

// A cartoon tree and a house, drawn around (0, 0) at their base, 24 units tall.
const SYMBOLS = `
<linearGradient id="map-sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8fd0e6"/><stop offset="1" stop-color="#6bb8d6"/></linearGradient>
<linearGradient id="map-land" x1="0" y1="0" x2="0.4" y2="1"><stop offset="0" stop-color="#bcd98f"/><stop offset=".55" stop-color="#cfd98e"/><stop offset="1" stop-color="#e0cf95"/></linearGradient>
<g id="map-tree">
  <ellipse cx="0" cy="0" rx="9" ry="2.6" fill="#1d2a26" opacity=".25"/>
  <path d="M-1.6 0 L-1 -11 L1 -11 L1.6 0Z" fill="#8a5a3b" stroke="#1d2a26" stroke-width="1.3" stroke-linejoin="round"/>
  <path d="M-11 -11c0-6 4-11 11-11s11 5 11 11c-4 2-18 2-22 0Z" fill="#a9c98c" stroke="#1d2a26" stroke-width="1.3" stroke-linejoin="round"/>
  <path d="M-6 -16c2-2 5-3 8-3" fill="none" stroke="#e4f2c9" stroke-width="1.6" stroke-linecap="round"/>
</g>
<g id="map-house">
  <ellipse cx="0" cy="0" rx="10" ry="2.6" fill="#1d2a26" opacity=".25"/>
  <path d="M-8 0V-10H8V0Z" fill="#fff4dc" stroke="#1d2a26" stroke-width="1.3" stroke-linejoin="round"/>
  <path d="M-10.5 -9 0 -19 10.5 -9Z" fill="#e2664f" stroke="#1d2a26" stroke-width="1.3" stroke-linejoin="round"/>
  <path d="M-2.5 0v-5.5h5V0" fill="#8a5a3b" stroke="#1d2a26" stroke-width="1.2"/>
</g>`;

export async function startMap(figure) {
  const holder = figure.querySelector('[data-map-canvas]');
  const points = JSON.parse(figure.dataset.points || '{}');
  let base;
  try {
    const res = await fetch(figure.dataset.basemap);
    base = await res.json();
  } catch {
    holder.querySelector('.map-wait').textContent = 'The map could not load.';
    return;
  }
  const project = (lon, lat) => [(lon - base.box[0]) * base.unit * base.cos, (base.box[3] - lat) * base.unit];

  const root = svg('svg', { viewBox: `0 0 ${base.width} ${base.height}`, role: 'img', 'aria-label': 'Map of where the species grows' });
  const defs = svg('defs', {}, root);
  defs.innerHTML = SYMBOLS;
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

  // Marks: GBIF areas when there are any, else the photos' places.
  const marks = svg('g', {}, root);
  const pins = [];
  const cells = points.cells ?? [];
  const tip = document.createElement('div');
  tip.className = 'map-tip';
  tip.hidden = true;
  const addPin = (lon, lat, size, label, symbol = '#map-tree', name = null) => {
    const [x, y] = project(lon, lat);
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
      addPin(lon, lat, 0.55 + 0.6 * Math.sqrt(n / max), `${n} sighting${n === 1 ? '' : 's'} here`);
    }
  } else {
    for (const p of points.places ?? []) {
      const n = p.photos.length;
      addPin(p.lon, p.lat, 0.8 + Math.min(0.6, Math.sqrt(n) * 0.18), `${p.name}: ${n} reference photo${n === 1 ? '' : 's'}`);
    }
  }
  if (points.world) addPin(points.world.lon, points.world.lat, 0.9, points.world.name, '#map-house', 'Unquillo');

  holder.replaceChildren(root, tip);

  // ---- view box: start on the marks, drag to pan, zoom around the pointer
  const xy = pins.map((p) => [p.x, p.y]);
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
