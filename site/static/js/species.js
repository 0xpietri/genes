// A species page: everything readable is already in the HTML. This adds the 3D tree and its
// simulated life, the day/night sky, the year wheel's needle, the animated leaf and the map.

import { mountAccount } from './account.js';
import { STAGE_LABEL, MONTHS, sampleAt, stageAt, indexForMonth } from './life.js';
import { t, num } from './i18n.js';

const body = document.body;
const $ = (sel) => document.querySelector(sel);
// The first month of the season (southern hemisphere) that month `m` is in: 1, 4, 7 or 10.
const SEASON_OF = (m) => [1, 4, 7, 10][Math.floor((m % 12) / 3)];

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.json();
}

function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch { /* private mode or blocked storage: the page works without it */ }
  return null;
}

// ---------------------------------------------------------------- day and night

function setupDayNight(stage) {
  const btn = $('[data-daynight]');
  const label = $('[data-daynight-label]');
  const saved = store('genes.mode');
  const hour = new Date().getHours();
  let night = saved ? saved === 'night' : hour < 7 || hour >= 20;
  const apply = (instant) => {
    body.dataset.mode = night ? 'night' : 'day';
    btn.setAttribute('aria-pressed', String(night));
    label.textContent = t(night ? 'Day' : 'Night');
    stage?.setNight(night, instant);
  };
  btn.addEventListener('click', () => { night = !night; store('genes.mode', night ? 'night' : 'day'); apply(false); });
  apply(true);
}

// ---------------------------------------------------------------- the year wheel

function setWheel(month) {
  const needle = $('[data-wheel-needle]');
  const text = $('[data-wheel-month]');
  if (!needle) return;
  needle.setAttribute('transform', `rotate(${((month - 0.5) / 12) * 360} 160 160)`);
  text.textContent = t(MONTHS[month - 1]);
}

// ---------------------------------------------------------------- the simulated life

function setupLife(stage, life, look) {
  const stages = Object.keys(look.stages);
  const n = life.samples.date.length;
  const age = $('[data-age]');
  const play = $('[data-play]');
  const readout = $('[data-readout]');
  const jumps = [...document.querySelectorAll('[data-jump]')];
  const seasons = [...document.querySelectorAll('[data-season]')];
  const speeds = [...document.querySelectorAll('[data-speed]')];
  const chart = $('[data-lifechart]');
  const cursor = $('[data-life-cursor]');
  const dot = $('[data-life-dot]');
  let speed = 4; // years per second
  let playing = false;
  let pos = 0;
  let shown = -1;

  // Open on a grown tree in the current month, so the first view is the species at its best.
  const month = new Date().getMonth() + 1;
  const adultAt = life.samples.age_days.findIndex((d) => d / 365.25 >= 60);
  pos = indexForMonth(life, Math.max(0, adultAt), month);

  function draw(i) {
    if (i === shown) return;
    shown = i;
    const s = sampleAt(life, i);
    const st = stageAt(life, i, stages);
    stage.show(st, s);
    age.value = String(i);
    const statusText = s.alive ? (s.status === 'healthy' ? '' : ` · ${t(s.status)}`) : '';
    readout.innerHTML = '';
    const parts = [
      [t('Year '), Math.floor(s.ageYears)],
      [` · ${t(MONTHS[s.month - 1])} ${s.year} · `, `${num(s.heightM)} m`],
      [s.alive ? t(' tall, crown ') : '', s.alive ? `${num(s.crownM)} m` : ''],
    ];
    for (const [t, b] of parts) {
      readout.append(t);
      if (b !== '') { const el = document.createElement('b'); el.textContent = b; readout.append(el); }
    }
    readout.append(` · ${t(STAGE_LABEL[st] ?? st)}${statusText}`);
    for (const b of jumps) b.setAttribute('aria-current', b.dataset.stagePic === st ? 'step' : 'false');
    const season = SEASON_OF(s.month);
    for (const b of seasons) b.setAttribute('aria-pressed', String(Number(b.dataset.season) === season));
    setWheel(s.month);
    if (chart) {
      const x = Number(chart.dataset.x0) + s.ageYears * Number(chart.dataset.sx);
      const y = Number(chart.dataset.y0) - s.heightM * Number(chart.dataset.sy);
      cursor.setAttribute('x1', x.toFixed(1));
      cursor.setAttribute('x2', x.toFixed(1));
      dot.setAttribute('cx', x.toFixed(1));
      dot.setAttribute('cy', y.toFixed(1));
    }
  }

  function setPlaying(on) {
    playing = on;
    play.setAttribute('aria-pressed', String(on));
    play.setAttribute('aria-label', t(on ? 'Pause' : "Play the tree's life"));
    if (on) {
      stage.preload(stages);
      if (Math.round(pos) >= n - 1) pos = 0;
      last = performance.now();
      requestAnimationFrame(tick);
    }
  }
  let last = 0;
  function tick(now) {
    if (!playing) return;
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    pos += dt * speed * 12;
    if (pos >= n - 1) { pos = n - 1; draw(n - 1); setPlaying(false); return; }
    draw(Math.floor(pos));
    requestAnimationFrame(tick);
  }

  play.addEventListener('click', () => setPlaying(!playing));
  age.addEventListener('input', () => { pos = Number(age.value); draw(pos); });
  for (const b of seasons) {
    b.addEventListener('click', () => { pos = indexForMonth(life, Math.round(pos), Number(b.dataset.season)); draw(pos); });
  }
  for (const b of speeds) {
    b.addEventListener('click', () => {
      speed = Number(b.dataset.speed);
      for (const o of speeds) o.setAttribute('aria-pressed', String(o === b));
    });
  }
  for (const b of jumps) {
    b.addEventListener('click', () => {
      setPlaying(false);
      pos = Number(b.dataset.jump);
      draw(pos);
      $('[data-stage]').scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }
  chart?.addEventListener('click', (e) => {
    const r = chart.getBoundingClientRect();
    const vb = chart.viewBox.baseVal;
    const x = ((e.clientX - r.left) / r.width) * vb.width;
    const years = (x - Number(chart.dataset.x0)) / Number(chart.dataset.sx);
    const days = Math.max(0, years * 365.25);
    const ages = life.samples.age_days;
    let i = ages.findIndex((d) => d >= days);
    if (i < 0) i = n - 1;
    pos = i;
    draw(i);
    $('[data-stage]').scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
  draw(pos);
  return { draw };
}

// ---------------------------------------------------------------- lazy parts

function whenNear(el, start) {
  if (!el) return;
  const io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) { io.disconnect(); start(); }
  }, { rootMargin: '300px' });
  io.observe(el);
}

async function main() {
  mountAccount();
  setWheel(new Date().getMonth() + 1);
  const canvas = $('[data-canvas]');
  const loading = $('[data-loading]');
  const lookUrl = body.dataset.look;
  try {
    const [sheet, look, life] = await Promise.all([
      getJSON(body.dataset.sheet),
      lookUrl ? getJSON(lookUrl) : null,
      body.dataset.lifecycle ? getJSON(body.dataset.lifecycle) : null,
    ]);
    whenNear($('[data-leaf]'), () => import('./leaf.js').then((m) => m.startLeaf($('[data-leaf-canvas]'), look)));
    whenNear($('[data-map]'), () => import('./map.js').then((m) => m.startMap($('[data-map]'))));
    if (!look) { setupDayNight(null); loading.hidden = true; body.dataset.ready = '1'; return; }
    const { Stage } = await import('./stage.js');
    const stage = new Stage(canvas, { look, sheet, modelsBase: body.dataset.models });
    setupDayNight(stage);
    $('[data-recentre]').addEventListener('click', () => stage.recentre());
    if (life) {
      setupLife(stage, life, look);
    } else {
      const m = new Date().getMonth() + 1;
      await stage.show('adult', { month: m, heightM: look.stages.adult.ref_height_m, crownM: look.stages.adult.ref_crown_m ?? 8, alive: true, mature: true, status: 'healthy', decay: 0 });
    }
    await stage.loadStage(stage.want);
    loading.hidden = true;
    body.dataset.ready = '1';
  } catch (err) {
    console.error(err);
    loading.textContent = t('The 3D model could not load.');
    body.dataset.error = String(err.message ?? err);
  }
}

main();
