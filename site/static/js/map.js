// Where the species lives: South America from Natural Earth, the provinces where the reference
// photos were taken, GBIF sightings per half-degree cell when fetched, and Unquillo. Drag to
// move, wheel or the buttons to zoom. SVG only, no tiles or outside services.

const NS = 'http://www.w3.org/2000/svg';

function svg(tag, attrs = {}, parent = null) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.append(node);
  return node;
}

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
  const land = svg('g', {}, root);
  const placed = new Set((points.places ?? []).map((p) => p.name));
  for (const c of base.countries) svg('path', { d: c.d, class: `country${c.iso === 'ARG' ? ' home' : ''}` }, land);
  for (const p of base.provinces) {
    const path = svg('path', { d: p.d, class: `province${placed.has(p.name) ? ' has' : ''}` }, land);
    svg('title', {}, path).textContent = p.name;
  }
  const marks = svg('g', {}, root);
  const half = 0.25;
  for (const [lon, lat, n] of points.cells ?? []) {
    const [x0, y0] = project(lon - half, lat + half);
    const [x1, y1] = project(lon + half, lat - half);
    const r = svg('rect', { x: x0, y: y0, width: x1 - x0, height: y1 - y0, class: 'cell', 'fill-opacity': Math.min(1, 0.25 + Math.log10(1 + n) / 2) }, marks);
    svg('title', {}, r).textContent = `${n} sightings`;
  }
  const scaled = [];
  const tip = document.createElement('div');
  tip.className = 'map-tip';
  tip.hidden = true;
  holder.append(tip);
  for (const p of points.places ?? []) {
    const [x, y] = project(p.lon, p.lat);
    const dot = svg('circle', { cx: x, cy: y, r: 4, class: 'place', tabindex: '0' }, marks);
    const label = `${p.name}: ${p.photos.length} reference photo${p.photos.length === 1 ? '' : 's'}`;
    dot.setAttribute('aria-label', label);
    const show = () => {
      const r = holder.getBoundingClientRect();
      const b = dot.getBoundingClientRect();
      tip.textContent = label;
      tip.style.left = `${b.left + b.width / 2 - r.left}px`;
      tip.style.top = `${b.top - r.top}px`;
      tip.hidden = false;
    };
    dot.addEventListener('pointerenter', show);
    dot.addEventListener('focus', show);
    dot.addEventListener('pointerleave', () => { tip.hidden = true; });
    dot.addEventListener('blur', () => { tip.hidden = true; });
    const text = svg('text', { x: x + 6, y: y + 4, class: 'label' }, marks);
    text.textContent = p.name;
    scaled.push({ dot, text, x, y, r: 4 + Math.sqrt(p.photos.length) * 1.5 });
  }
  if (points.world) {
    const [x, y] = project(points.world.lon, points.world.lat);
    const star = svg('path', { class: 'world' }, marks);
    svg('title', {}, star).textContent = points.world.name;
    scaled.push({ star, x, y, r: 10 });
  }

  holder.replaceChildren(root, tip);

  // ---- view box: start on the points, drag to pan, zoom around the pointer
  const all = [...(points.places ?? []).map((p) => project(p.lon, p.lat)),
    ...(points.cells ?? []).map(([lon, lat]) => project(lon, lat))];
  if (points.world) all.push(project(points.world.lon, points.world.lat));
  const xs = all.map((p) => p[0]);
  const ys = all.map((p) => p[1]);
  const home = all.length
    ? (() => {
      const pad = 40;
      let x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad, y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
      const aspect = 16 / 10;
      const w = Math.max(x1 - x0, (y1 - y0) * aspect);
      const h = w / aspect;
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      return { x: cx - w / 2, y: cy - h / 2, w, h };
    })()
    : { x: 0, y: 0, w: base.width, h: base.height };
  let vb = { ...home };
  function draw() {
    root.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    const px = vb.w / Math.max(1, holder.clientWidth); // view units per screen pixel
    for (const s of scaled) {
      if (s.dot) {
        s.dot.setAttribute('r', (s.r * px).toFixed(2));
        s.text.setAttribute('x', (s.x + (s.r + 4) * px).toFixed(2));
        s.text.setAttribute('y', (s.y + 4 * px).toFixed(2));
        s.text.style.fontSize = `${12 * px}px`;
      } else {
        const r = s.r * px;
        const d = [];
        for (let i = 0; i < 10; i++) {
          const a = -Math.PI / 2 + (i * Math.PI) / 5;
          const rr = i % 2 ? r * 0.45 : r;
          d.push(`${(s.x + Math.cos(a) * rr).toFixed(2)} ${(s.y + Math.sin(a) * rr).toFixed(2)}`);
        }
        s.star.setAttribute('d', `M${d.join('L')}Z`);
      }
    }
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
