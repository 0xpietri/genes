// The species page's 3D stage: the look's own models (one per life stage), painted with the
// look's palette and the sheet's season, scaled to the simulated tree, under the day or night
// sky. Turn with a drag, zoom with the wheel or a pinch.

import * as THREE from '/static/vendor/three/three.module.js';
import { GLTFLoader } from '/static/vendor/three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from '/static/vendor/three/addons/controls/OrbitControls.js';
import { MeshoptDecoder } from '/static/vendor/three/addons/libs/meshopt_decoder.module.js';
import { partAmounts, foliageTones } from '/static/phenology.js';
import { withOrderReveal } from '/static/paint.js';
import { Sky } from './sky.js';

const PART_REVEAL = ['foliage', 'flowers', 'fruit'];

function toonGradient() {
  const tex = new THREE.DataTexture(new Uint8Array([80, 150, 210, 255]), 4, 1, THREE.RedFormat);
  tex.minFilter = tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
}

function blobTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  r.addColorStop(0, 'rgba(0,0,0,0.5)');
  r.addColorStop(0.6, 'rgba(0,0,0,0.25)');
  r.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = r;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

/** The disc's edge: opaque in the middle, fading out towards the rim. */
function groundFade() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d');
  const r = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  r.addColorStop(0, '#fff');
  r.addColorStop(0.55, '#f2f2f2');
  r.addColorStop(1, '#000');
  g.fillStyle = r;
  g.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}

/** Drawn speckles of dry grass and soil, until marcos's painted soil loads. */
function groundTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d');
  g.fillStyle = '#fff';
  g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 2600; i++) {
    g.fillStyle = `rgba(${Math.random() < 0.5 ? '90,80,50' : '210,200,150'},${0.06 + Math.random() * 0.1})`;
    g.fillRect(Math.random() * 512, Math.random() * 512, 2 + Math.random() * 3, 1 + Math.random() * 2);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(8, 8);
  return t;
}

// One tile of the painted soil covers this many metres; the disc is 120 m across.
const GROUND_TILE_M = 5;

export class Stage {
  constructor(canvas, { look, sheet, modelsBase }) {
    this.look = look;
    this.sheet = sheet;
    this.modelsBase = modelsBase;
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(35, 1, 0.05, 1200);
    // Low, near the base of the trunk, looking up a little so the crown shows whole.
    this.camera.position.set(9, 1.2, 16);
    this.controls = new OrbitControls(this.camera, canvas);
    Object.assign(this.controls, {
      enableDamping: true, dampingFactor: 0.08, minDistance: 0.8, maxDistance: 90,
      maxPolarAngle: Math.PI / 2 - 0.04, autoRotate: true, autoRotateSpeed: 0.5, enablePan: false,
    });
    this.userZoom = 1;
    this.controls.addEventListener('start', () => { this.controls.autoRotate = false; this.interacting = true; });
    this.controls.addEventListener('end', () => {
      this.interacting = false;
      const fit = this.fitDistance();
      if (fit > 0) this.userZoom = this.camera.position.distanceTo(this.controls.target) / fit;
    });
    this.sky = new Sky(this.scene, this.renderer);

    this.ground = new THREE.Mesh(
      new THREE.CircleGeometry(60, 96),
      new THREE.MeshLambertMaterial({ map: groundTexture(), alphaMap: groundFade(), transparent: true, depthWrite: false, color: '#a3a56f' }),
    );
    this.groundPainted = false;
    new THREE.TextureLoader().load('/static/site/art/scene/ground.webp', (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.wrapS = tex.wrapT = THREE.MirroredRepeatWrapping;
      tex.repeat.set(120 / GROUND_TILE_M, 120 / GROUND_TILE_M);
      tex.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
      const old = this.ground.material.map;
      this.ground.material.map = tex;
      this.ground.material.needsUpdate = true;
      old.dispose();
      this.groundPainted = true;
    });
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.renderOrder = -1;
    this.scene.add(this.ground);
    this.blob = new THREE.Mesh(
      new THREE.PlaneGeometry(1, 1),
      new THREE.MeshBasicMaterial({ map: blobTexture(), transparent: true, depthWrite: false }),
    );
    this.blob.rotation.x = -Math.PI / 2;
    this.blob.position.y = 0.01;
    this.scene.add(this.blob);

    this.holder = new THREE.Group(); // swayed by the wind
    this.scene.add(this.holder);
    this.loader = new GLTFLoader();
    this.loader.setMeshoptDecoder(MeshoptDecoder);
    this.cache = new Map();
    this.gradient = toonGradient();
    this.reveal = Object.fromEntries(PART_REVEAL.map((p) => [p, { value: 1 }]));
    this.tone = {
      uFrom: { value: new THREE.Color() }, uTo: { value: new THREE.Color() },
      uEdge: { value: 2 }, uLowest: { value: 0 },
    };
    this.current = null; // { stage, root, size }
    this.want = null;
    this.state = null;
    this.clock = new THREE.Timer();
    this.visible = true;
    new ResizeObserver(() => this.resize()).observe(canvas);
    new IntersectionObserver(([e]) => { this.visible = e.isIntersecting; }).observe(canvas);
    this.resize();
    this.renderer.setAnimationLoop(() => this.frame());
  }

  resize() {
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  setNight(night, instant) { this.sky.setNight(night, instant); }

  modelUrl(stage) { return `${this.modelsBase}${stage}-a.lod0.glb`; }

  async loadStage(stage) {
    if (!this.cache.has(stage)) {
      this.cache.set(stage, this.loader.loadAsync(this.modelUrl(stage)).then((gltf) => this.prepare(gltf.scene)));
    }
    return this.cache.get(stage);
  }

  /** Paints a fresh model once: toon bands from the look's palette, clumps revealed by _order. */
  prepare(root) {
    const palette = this.look.palette ?? {};
    root.traverse((obj) => {
      if (!obj.isMesh) return;
      const part = obj.material.name || obj.name;
      const base = obj.material;
      const tones = palette[part];
      const lit = tones?.lit ?? tones?.mature?.lit;
      const mat = new THREE.MeshToonMaterial({
        color: lit ? new THREE.Color(lit) : base.color, gradientMap: this.gradient,
        map: base.map ?? null, alphaTest: base.alphaTest || (base.map ? 0.5 : 0), side: THREE.DoubleSide,
      });
      mat.name = part;
      if (PART_REVEAL.includes(part) && obj.geometry.getAttribute('_order')) {
        withOrderReveal(mat, this.reveal[part], part === 'foliage' && palette.foliage && !palette.foliage.lit ? this.tone : null);
      }
      obj.material = mat;
      obj.userData.part = part;
    });
    const box = new THREE.Box3().setFromObject(root);
    const size = box.getSize(new THREE.Vector3());
    return { root, size, box };
  }

  /** Shows sample `s` (from life.js's sampleAt) as stage `stage`. */
  async show(stage, s) {
    this.state = { stage, s };
    this.want = stage;
    const model = await this.loadStage(stage);
    if (this.want !== stage) return;
    if (this.current?.stage !== stage) {
      if (this.current) this.holder.remove(this.current.root);
      this.current = { stage, ...model };
      this.holder.add(model.root);
      this.snap = true; // a new model: frame it at once
    }
    this.place();
  }

  place() {
    if (!this.current || !this.state) return;
    const { s } = this.state;
    const { root, size, stage } = this.current;
    const live = !['dead_standing', 'fallen'].includes(stage);
    let sy;
    let sxz;
    if (stage === 'fallen') {
      // A lying trunk: scale by the height the tree died with against the standing dead model.
      const ref = this.look.stages?.dead_standing?.ref_height_m ?? 8;
      sy = sxz = THREE.MathUtils.clamp(s.heightM / ref, 0.3, 1.6);
    } else {
      sy = s.heightM / Math.max(size.y, 0.05);
      const width = Math.max(size.x, size.z, 0.05);
      sxz = live ? s.crownM / width : sy;
      sxz = THREE.MathUtils.clamp(sxz, sy * 0.65, sy * 1.6);
    }
    root.scale.set(sxz, sy, sxz);
    root.position.y = stage === 'fallen' ? -s.decay * 0.6 * size.y * sy : 0;
    const crown = Math.max(size.x, size.z) * sxz;
    this.blob.scale.set(crown * 1.25, crown * 1.25, 1);
    this.applySeason();
  }

  applySeason() {
    if (!this.state) return;
    const { s } = this.state;
    const a = partAmounts(this.sheet, s.month);
    const vigour = s.status === 'dying' ? 0.5 : s.status === 'stressed' ? 0.8 : 1;
    this.reveal.foliage.value = s.alive ? a.foliage * vigour : 0;
    this.reveal.flowers.value = s.alive && s.mature ? a.flowers * vigour : 0;
    this.reveal.fruit.value = s.alive && s.mature ? a.fruit * vigour : 0;
    const t = foliageTones(this.sheet, s.month);
    const tones = this.look.palette?.foliage;
    if (t && tones && !tones.lit) {
      const lit = (name) => (tones[name] ?? tones.mature ?? Object.values(tones)[0]).lit;
      this.tone.uFrom.value.set(lit(t.from));
      this.tone.uTo.value.set(lit(t.to));
      const amount = this.reveal.foliage.value;
      this.tone.uEdge.value = t.share > 0 ? (t.lowest ? amount * t.share : amount * (1 - t.share)) : 2;
      this.tone.uLowest.value = t.lowest ? 1 : 0;
    }
    this.blob.material.opacity = 0.35 + 0.65 * this.reveal.foliage.value;
    this.current?.root.traverse((o) => {
      if (o.isMesh && PART_REVEAL.includes(o.userData.part)) o.visible = this.reveal[o.userData.part].value > 0;
    });
  }

  /** Distance at which the whole tree fits the view. */
  fitDistance() {
    if (!this.current) return 0;
    const box = new THREE.Box3().setFromObject(this.current.root);
    const size = box.getSize(new THREE.Vector3());
    const r = Math.max(size.y * 0.8, Math.max(size.x, size.z) * 0.7, 1.1);
    const vfov = THREE.MathUtils.degToRad(this.camera.fov / 2);
    const hfov = Math.atan(Math.tan(vfov) * this.camera.aspect);
    return r / Math.tan(Math.min(vfov, hfov)) + 0.5;
  }

  recentre() {
    this.userZoom = 1;
    this.controls.autoRotate = true;
  }

  /** Keeps the tree in view while it grows, respecting the visitor's zoom. */
  follow(dt) {
    if (!this.current || this.interacting) return;
    const box = new THREE.Box3().setFromObject(this.current.root);
    const centre = box.getCenter(new THREE.Vector3());
    // Aim at the middle of the tree: from a low camera the crown fills the top of the view.
    const targetY = Math.max(0.15, centre.y * 0.92);
    const k = this.snap ? 1 : 1 - Math.exp(-dt * 3);
    this.snap = false;
    const tgt = this.controls.target;
    tgt.y += (targetY - tgt.y) * k;
    tgt.x += (0 - tgt.x) * k;
    tgt.z += (0 - tgt.z) * k;
    const want = this.fitDistance() * this.userZoom;
    const off = this.camera.position.clone().sub(tgt);
    const d = off.length();
    off.setLength(d + (want - d) * k);
    this.camera.position.copy(tgt).add(off);
  }

  frame() {
    this.clock.update();
    const dt = Math.min(this.clock.getDelta(), 0.1);
    if (!this.visible) return;
    const t = this.clock.getElapsed();
    this.sky.update(dt, t);
    this.sky.groundColour(this.ground.material.color, this.groundPainted);
    // A light wind: the crown leans a little, more when it is in leaf.
    const leafy = this.state?.s.alive ? 1 : 0.2;
    this.holder.rotation.z = Math.sin(t * 0.9) * 0.006 * leafy;
    this.holder.rotation.x = Math.sin(t * 0.63 + 1) * 0.004 * leafy;
    this.follow(dt);
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  /** Loads the other stages when the browser is idle, so playing never waits. */
  preload(stages) {
    const next = stages.filter((s) => !this.cache.has(s));
    const idle = window.requestIdleCallback ?? ((f) => setTimeout(f, 300));
    const one = () => {
      const s = next.shift();
      if (!s) return;
      this.loadStage(s).finally(() => idle(one));
    };
    idle(one);
  }
}
