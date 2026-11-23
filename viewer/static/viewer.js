// genes viewer (spec §14): the catalog, and a page per species where its models are reviewed.
// Plain ES modules, no build step; three.js is vendored under ./vendor/three/.

import * as THREE from './vendor/three/three.module.js';
import { GLTFLoader } from './vendor/three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from './vendor/three/addons/controls/OrbitControls.js';
import { MeshoptDecoder } from './vendor/three/addons/libs/meshopt_decoder.module.js';
import { partAmounts, MONTHS } from './phenology.js';

const app = document.getElementById('app');
const PERSON_HEIGHT_M = 1.75;
const STAGE_ORDER = ['seedling', 'sapling', 'young', 'adult', 'old', 'dead_standing', 'fallen', 'tuft'];
const STAGE_LABEL = {
  seedling: 'Seedling', sapling: 'Sapling', young: 'Young', adult: 'Adult', old: 'Old',
  dead_standing: 'Dead, standing', fallen: 'Fallen', tuft: 'Tuft',
};

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) node.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat()) if (c !== null && c !== undefined) node.append(c);
  return node;
}

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.json();
}

function fail(message) {
  app.replaceChildren(el('p', { class: 'error', text: message }));
  document.body.dataset.error = message;
}

// ------------------------------------------------------------------ catalog page

function renderCatalog(catalog) {
  const cards = catalog.species.map((sp) => el('li', { class: 'card' },
    el('a', { href: `/species/${sp.id}/` },
      el('div', { class: 'name', text: sp.names.es?.[0] ?? sp.id }),
      el('div', { class: 'sci', text: sp.scientific_name }),
      el('div', { class: 'meta', text: [sp.names.en?.[0], sp.growth_form ?? sp.class, sp.status_in_sierras_chicas].filter(Boolean).join(' · ') }),
    )));
  app.replaceChildren(el('section', { class: 'catalog' },
    el('h1', { text: `Species (${catalog.species.length})` }),
    cards.length ? el('ul', { class: 'cards' }, cards) : el('p', { class: 'empty', text: 'No species yet.' }),
    el('p', { class: 'foot', text: `Catalog release ${catalog.catalog}.` }),
  ));
  document.title = 'genes';
  document.body.dataset.ready = '1';
}

// ------------------------------------------------------------------ species page

const ORDER_CHUNK_VERTEX = '#include <common>\nattribute float _order;\nvarying float vOrder;';
const ORDER_CHUNK_FRAGMENT = '#include <common>\nuniform float uAmount;\nvarying float vOrder;';

// Reveal clumps whose _order is under the part's amount (spec §6.3).
function withOrderReveal(material, uniform) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uAmount = uniform;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', ORDER_CHUNK_VERTEX)
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvOrder = _order;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', ORDER_CHUNK_FRAGMENT)
      .replace('#include <clipping_planes_fragment>', '#include <clipping_planes_fragment>\nif (vOrder > uAmount) discard;');
  };
  material.customProgramCacheKey = () => 'genes-order';
  return material;
}

function toonGradient() {
  // Three flat bands: a rough preview of the world's painter, not the painter itself (spec §8).
  const data = new Uint8Array([90, 170, 255]);
  const tex = new THREE.DataTexture(data, 3, 1, THREE.RedFormat);
  tex.minFilter = tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
}

function litColour(palette, part, month, amounts) {
  const tones = palette?.[part];
  if (!tones) return null;
  if (tones.lit) return tones.lit;
  if (part === 'foliage' && amounts.foliageAutumn && tones.autumn) return tones.autumn.lit;
  return (tones.mature ?? Object.values(tones)[0]).lit;
}

function fmtRange(r, unit) {
  if (!r || typeof r !== 'object') return '';
  if ('value' in r) return r.value;
  const typ = r.typical !== undefined ? ` (usually ${r.typical})` : '';
  return `${r.min}–${r.max}${unit ? ' ' + unit : ''}${typ}`;
}

const FACTS = [
  ['plant.size.adult_height_m', 'Adult height', 'm'],
  ['plant.size.crown_width_m', 'Crown width', 'm'],
  ['plant.size.trunk_dbh_m', 'Trunk diameter', 'm'],
  ['plant.life.first_flowering_years', 'First flowers at', 'years'],
  ['plant.life.lifespan_years', 'Lifespan', 'years'],
  ['plant.water.rainfall_mm_year', 'Rainfall', 'mm/year'],
  ['plant.water.drought_tolerance', 'Drought tolerance', ''],
  ['plant.water.root_depth_m', 'Root depth', 'm'],
  ['plant.climate.frost_kill_c_adult', 'Frost kills an adult at', '°C'],
  ['plant.wood.density_kg_m3', 'Wood density', 'kg/m³'],
];

function dig(obj, path) {
  return path.split('.').reduce((o, k) => (o && typeof o === 'object' ? o[k] : undefined), obj);
}

function monthsText(phase) {
  return phase?.months ? phase.months.map((m) => MONTHS[m - 1]).join(', ') : null;
}

async function renderSpecies(id) {
  const catalog = await getJSON('/v1/catalog.json');
  const entry = catalog.species.find((s) => s.id === id);
  if (!entry) return fail(`Species "${id}" is not in the catalog.`);
  const params = new URLSearchParams(location.search);
  const lookEntry = entry.looks.find((l) => String(l.version) === params.get('look')) ?? entry.looks.at(-1);
  const [budgets, look] = await Promise.all([
    getJSON('/v1/budgets.json'),
    lookEntry ? getJSON(lookEntry.path) : Promise.resolve(null),
  ]);
  const sheetEntry = entry.sheets.find((s) => s.version === look?.for_sheet) ?? entry.sheets.at(-1);
  const sheet = await getJSON(sheetEntry.path);
  const refs = entry.references ? await getJSON(entry.references.path) : null;
  document.title = `${sheet.names.es[0]} · genes`;

  // ---- layout
  const view = el('div', { class: 'view' });
  const panel = el('aside', { class: 'panel' });
  app.replaceChildren(el('section', { class: 'species' }, view, panel));

  panel.append(
    el('h1', { text: sheet.names.es[0] }),
    el('div', { class: 'en', text: sheet.names.en.join(', ') }),
    el('div', { class: 'sci', text: `${sheet.scientific_name}${sheet.authority ? ' ' + sheet.authority : ''}${sheet.family ? ' · ' + sheet.family : ''}` }),
    el('p', { class: 'summary', text: sheet.summary.es }),
    el('p', { class: 'summary en', text: sheet.summary.en }),
  );

  if (!look) {
    panel.append(el('p', { class: 'empty', text: 'No look yet: only the sheet.' }));
    renderFacts(panel, sheet);
    document.body.dataset.ready = '1';
    return;
  }

  // ---- three.js scene
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  view.append(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.05, 500);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.autoRotateSpeed = 0.8;
  scene.add(new THREE.HemisphereLight(0xdfe9f3, 0x8a7a5c, 1.4));
  const sun = new THREE.DirectionalLight(0xfff1d6, 2.2);
  sun.position.set(8, 14, 6);
  scene.add(sun);
  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(30, 64),
    new THREE.MeshLambertMaterial({ color: 0xc9bf8f }),
  );
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);
  const grid = new THREE.GridHelper(20, 20, 0x9c9070, 0xb3a982);
  grid.position.y = 0.002;
  scene.add(grid);
  const person = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.2, PERSON_HEIGHT_M - 0.4, 6, 12),
    new THREE.MeshLambertMaterial({ color: 0x5b6c8a }),
  );
  person.position.y = PERSON_HEIGHT_M / 2;
  scene.add(person);

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const cache = new Map();
  const gradient = toonGradient();
  const uniforms = { foliage: { value: 1 }, flowers: { value: 0 }, fruit: { value: 0 } };

  const stages = Object.keys(look.stages).sort((a, b) => STAGE_ORDER.indexOf(a) - STAGE_ORDER.indexOf(b));
  const state = {
    stage: params.get('stage') ?? (stages.includes('adult') ? 'adult' : stages[0]),
    variant: 'a',
    lod: look.lods[0],
    month: Number(params.get('month')) || new Date().getMonth() + 1,
    person: true,
    turn: true,
    painted: false,
  };
  let current = null;
  let currentInfo = null;

  function resize() {
    const w = view.clientWidth, h = view.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(h, 1);
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(view);

  function frame(angle = 'side') {
    const box = new THREE.Box3();
    if (current) box.expandByObject(current);
    if (state.person) box.expandByObject(person);
    const size = box.getSize(new THREE.Vector3());
    const centre = box.getCenter(new THREE.Vector3());
    const radius = Math.max(size.x, size.y, size.z, 1) * 0.75;
    const dist = radius / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const dir = {
      side: new THREE.Vector3(0.2, 0.15, 1),
      below: new THREE.Vector3(0.1, -0.35, 1),
      above: new THREE.Vector3(0.2, 1.2, 0.8),
      detail: new THREE.Vector3(0.3, 0.1, 1),
    }[angle] ?? new THREE.Vector3(0.2, 0.15, 1);
    const target = angle === 'below' ? new THREE.Vector3(centre.x, centre.y * 1.3, centre.z) : centre;
    const d = angle === 'detail' ? dist * 0.45 : dist;
    camera.position.copy(target).addScaledVector(dir.normalize(), d);
    if (angle === 'below') camera.position.y = Math.max(camera.position.y, 0.3);
    controls.target.copy(target);
    controls.update();
  }

  function applyMaterials(root) {
    const amounts = partAmounts(sheet, state.month);
    for (const part of ['foliage', 'flowers', 'fruit']) uniforms[part].value = amounts[part];
    root.traverse((obj) => {
      if (!obj.isMesh) return;
      const part = obj.material.name || obj.name;
      if (!obj.userData.original) obj.userData.original = obj.material;
      const base = obj.userData.original;
      let mat;
      if (state.painted) {
        const hex = litColour(look.palette, part, state.month, amounts);
        mat = new THREE.MeshToonMaterial({
          color: hex ? new THREE.Color(hex) : base.color, gradientMap: gradient, map: base.map, alphaTest: base.alphaTest,
        });
      } else {
        mat = base.clone();
      }
      mat.name = part;
      mat.side = THREE.DoubleSide;
      if (part in uniforms) {
        if (obj.geometry.getAttribute('_order')) withOrderReveal(mat, uniforms[part]);
        obj.visible = uniforms[part].value > 0;
      }
      obj.material = mat;
    });
  }

  async function loadModel() {
    const name = `${state.stage}-${state.variant}.${state.lod}.glb`;
    const url = `/v1/species/${id}/looks/${lookEntry.version}/${name}`;
    if (!cache.has(url)) cache.set(url, loader.loadAsync(url));
    const gltf = await cache.get(url);
    if (current) scene.remove(current);
    current = gltf.scene;
    applyMaterials(current);
    scene.add(current);
    const info = current.userData.genes ?? {};
    const crown = info.ref_crown_m ?? look.stages[state.stage].ref_crown_m ?? 2;
    person.position.x = crown / 2 + 0.8;
    let tris = 0;
    current.traverse((o) => {
      if (o.isMesh) tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
    });
    const fileMeta = lookEntry.files.find((f) => f.path.endsWith('/' + name));
    const box = new THREE.Box3().setFromObject(current);
    currentInfo = {
      name, tris, bytes: fileMeta?.bytes ?? 0, height: box.max.y - box.min.y,
      triBudget: budgets.triangles?.[state.lod]?.[state.stage],
    };
    renderStats();
    frame();
    document.body.dataset.ready = '1';
  }

  // ---- controls
  const stageSelect = el('select', { 'aria-label': 'Stage', onchange: (e) => { state.stage = e.target.value; state.variant = 'a'; buildVariants(); loadModel().catch((e2) => fail(String(e2))); } },
    stages.map((s) => el('option', { value: s, selected: s === state.stage, text: STAGE_LABEL[s] ?? s })));
  const variantSeg = el('div', { class: 'seg', role: 'group', 'aria-label': 'Variant' });
  function buildVariants() {
    const n = look.stages[state.stage].variants;
    variantSeg.replaceChildren(...Array.from({ length: n }, (_, i) => {
      const v = String.fromCharCode(97 + i);
      return el('button', { type: 'button', 'aria-pressed': String(v === state.variant), text: v.toUpperCase(),
        onclick: () => { state.variant = v; buildVariants(); loadModel().catch((e) => fail(String(e))); } });
    }));
  }
  buildVariants();
  const lodSeg = el('div', { class: 'seg', role: 'group', 'aria-label': 'Detail' });
  function buildLods() {
    lodSeg.replaceChildren(...look.lods.map((l) => el('button', {
      type: 'button', 'aria-pressed': String(l === state.lod), text: l === 'lod0' ? 'Close' : l === 'lod1' ? 'Far' : l,
      onclick: () => { state.lod = l; buildLods(); loadModel().catch((e) => fail(String(e))); },
    })));
  }
  buildLods();
  const monthNote = el('div', { class: 'month-note' });
  const monthLabel = el('label', { for: 'month', text: '' });
  const monthInput = el('input', { id: 'month', type: 'range', min: 1, max: 12, step: 1, value: state.month,
    oninput: (e) => { state.month = Number(e.target.value); updateMonth(); if (current) applyMaterials(current); } });
  function updateMonth() {
    const a = partAmounts(sheet, state.month);
    monthLabel.textContent = MONTHS[state.month - 1];
    const parts = [`leaves ${Math.round(a.foliage * 100)} %`];
    if (a.flowers > 0) parts.push('flowering');
    if (a.fruit > 0) parts.push('fruiting');
    monthNote.textContent = `${parts.join(' · ')} (a preview from the sheet's months; the world decides with its weather)`;
  }
  updateMonth();
  const check = (key, label) => el('label', {},
    el('input', { type: 'checkbox', checked: state[key], onchange: (e) => {
      state[key] = e.target.checked;
      if (key === 'person') person.visible = state.person;
      if (key === 'turn') controls.autoRotate = state.turn;
      if (key === 'painted' && current) applyMaterials(current);
    } }), ` ${label}`);
  controls.autoRotate = state.turn;

  panel.append(
    el('h2', { text: 'Model' }),
    el('div', { class: 'row' }, el('label', { text: 'Stage' }), stageSelect),
    el('div', { class: 'row' }, el('label', { text: 'Variant' }), variantSeg),
    el('div', { class: 'row' }, el('label', { text: 'Detail' }), lodSeg),
    el('div', { class: 'row' }, monthLabel, monthInput, monthNote),
    el('div', { class: 'row checks' }, check('person', 'Person 1.75 m'), check('turn', 'Turn'), check('painted', 'Painted preview')),
  );
  const stats = el('div', { class: 'stats' });
  panel.append(stats);
  function renderStats() {
    if (!currentInfo) return;
    const over = currentInfo.triBudget !== undefined && currentInfo.tris > currentInfo.triBudget;
    stats.replaceChildren(
      el('span', { text: 'File' }), el('span', { text: currentInfo.name }),
      el('span', { text: 'Triangles' }), el('span', { class: over ? 'over' : '', text: `${currentInfo.tris.toLocaleString('en')} of ${currentInfo.triBudget?.toLocaleString('en') ?? '?'}` }),
      el('span', { text: 'Size' }), el('span', { text: `${(currentInfo.bytes / 1024).toFixed(0)} KB` }),
      el('span', { text: 'Height' }), el('span', { text: `${currentInfo.height.toFixed(2)} m` }),
    );
  }

  // ---- recognisable traits
  panel.append(el('h2', { text: 'Recognisable by' }),
    el('ul', { class: 'facts' }, look.recognisable.map((r) => el('li', { text: r.trait }))));

  renderFacts(panel, sheet);

  // ---- references
  if (refs?.photos?.length) {
    panel.append(el('h2', { text: 'Reference photos' }));
    panel.append(el('div', { class: 'refs' }, refs.photos.map((p) => el('div', { class: 'ref' },
      p.file ? el('img', { src: `/v1/species/${id}/references/${p.file}`, alt: p.shows.join(', '), loading: 'lazy' }) : null,
      el('div', {}, el('a', { href: p.url, target: '_blank', rel: 'noopener', text: p.shows.join(', ') })),
      el('div', { class: 'who', text: `${p.author} · ${p.licence.toUpperCase()}${p.file ? '' : ' · link only'}` }),
      el('button', { type: 'button', text: `View from ${p.angle}`, onclick: () => { state.turn = false; controls.autoRotate = false; frame(p.angle); } }),
    ))));
  }

  panel.append(el('p', { class: 'foot', text: `Look ${look.look} (generator ${look.generator}) · sheet ${sheet.version} · catalog ${catalog.catalog}` }));

  resize();
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
  await loadModel();
}

function renderFacts(panel, sheet) {
  const items = [];
  for (const [path, label, unit] of FACTS) {
    const v = dig(sheet, path);
    if (v) items.push(el('li', {}, el('span', { class: 'k', text: `${label}: ` }), fmtRange(v, unit), el('span', { class: 'src', text: ` [${v.source.join(', ')}]` })));
  }
  const ph = sheet.plant?.phenology;
  if (ph) {
    if (ph.leaf_habit) items.push(el('li', {}, el('span', { class: 'k', text: 'Leaves: ' }), ph.leaf_habit.replace('_', '-')));
    for (const [key, label] of [['leaf_out', 'Leaf-out'], ['flowering', 'Flowers'], ['fruiting', 'Fruit'], ['leaf_fall', 'Leaf fall']]) {
      const text = monthsText(ph[key]);
      if (text) items.push(el('li', {}, el('span', { class: 'k', text: `${label}: ` }), text,
        ph[key].trigger ? ` (after ${ph[key].trigger.replaceAll('_', ' ')})` : '', el('span', { class: 'src', text: ` [${ph[key].source.join(', ')}]` })));
    }
  }
  panel.append(el('h2', { text: 'Facts' }), el('ul', { class: 'facts' }, items));
  panel.append(el('h2', { text: 'Sources' }), el('ol', { class: 'sources' }, sheet.sources.map((s) => el('li', {},
    `[${s.id}] `, s.url ? el('a', { href: s.url, target: '_blank', rel: 'noopener', text: s.title }) : s.title,
    s.accessed ? ` (accessed ${s.accessed})` : ''))));
}

// ------------------------------------------------------------------ router

async function main() {
  try {
    const m = location.pathname.match(/^\/species\/([a-z0-9-]+)\/?$/);
    if (m) await renderSpecies(m[1]);
    else renderCatalog(await getJSON('/v1/catalog.json'));
  } catch (err) {
    console.error(err);
    fail(String(err.message ?? err));
  }
}

main();
