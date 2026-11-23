// One bipinnate leaf in 3D, moving in the wind: a stalk, pairs of pinnae, and on each pinna
// many pairs of small leaflets. Drawn from the look's leaf type and colours; an illustration
// of the leaf's form, not a measured model.

import * as THREE from '/static/vendor/three/three.module.js';
import { OrbitControls } from '/static/vendor/three/addons/controls/OrbitControls.js';

const PINNA_PAIRS = 2;
const LEAFLET_PAIRS = 22;

function leafletGeometry() {
  // A narrow oblong leaflet, rounded at both ends, slightly cupped.
  const s = new THREE.Shape();
  s.moveTo(0, 0);
  s.bezierCurveTo(0.012, 0.004, 0.016, 0.03, 0.012, 0.05);
  s.bezierCurveTo(0.008, 0.064, -0.008, 0.064, -0.012, 0.05);
  s.bezierCurveTo(-0.016, 0.03, -0.012, 0.004, 0, 0);
  const g = new THREE.ShapeGeometry(s, 6);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) pos.setZ(i, Math.abs(pos.getX(i)) * 0.6);
  g.computeVertexNormals();
  return g;
}

export function startLeaf(canvas, look) {
  if (!canvas || !look) return;
  const palette = look.palette?.foliage ?? {};
  const green = new THREE.Color(palette.mature?.lit ?? palette.lit ?? '#8fa155');
  const young = new THREE.Color(palette.new?.lit ?? '#b5c46a');
  const stalkColour = new THREE.Color('#7d7a4e');

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.01, 20);
  camera.position.set(0.15, 0.25, 0.75);
  const controls = new OrbitControls(camera, canvas);
  Object.assign(controls, { enableDamping: true, autoRotate: true, autoRotateSpeed: 1.2, enablePan: false, minDistance: 0.25, maxDistance: 2 });
  controls.target.set(0, 0.16, 0);
  controls.addEventListener('start', () => { controls.autoRotate = false; });
  scene.add(new THREE.HemisphereLight(0xeef6ff, 0x3a4a30, 1.6));
  const sun = new THREE.DirectionalLight(0xfff3dc, 2.2);
  sun.position.set(1, 2, 1.5);
  scene.add(sun);

  const stalkMat = new THREE.MeshStandardMaterial({ color: stalkColour, roughness: 0.8 });
  const leafMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.65, side: THREE.DoubleSide });
  const leaf = new THREE.Group();
  scene.add(leaf);

  // Stalk (petiole and short rachis), slightly arched.
  const stalkCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0.08, 0.01), new THREE.Vector3(0, 0.16, 0.0),
  ]);
  leaf.add(new THREE.Mesh(new THREE.TubeGeometry(stalkCurve, 20, 0.0035, 6), stalkMat));

  const pinnae = [];
  const geom = leafletGeometry();
  const count = PINNA_PAIRS * 2 * LEAFLET_PAIRS * 2;
  const leaflets = new THREE.InstancedMesh(geom, leafMat, count);
  const colour = new THREE.Color();
  let k = 0;
  for (let p = 0; p < PINNA_PAIRS * 2; p++) {
    const side = p % 2 ? -1 : 1;
    const level = Math.floor(p / 2);
    const pivot = new THREE.Group();
    pivot.position.set(0, 0.11 + level * 0.05, 0);
    pivot.rotation.z = side * (1.0 - level * 0.45);
    pivot.rotation.y = side * 0.25;
    const length = 0.22 - level * 0.02;
    const rachis = new THREE.Mesh(new THREE.CylinderGeometry(0.0018, 0.0026, length, 5), stalkMat);
    rachis.position.y = length / 2;
    pivot.add(rachis);
    leaf.add(pivot);
    pinnae.push({ pivot, side, length, first: k, phase: p * 1.7 });
    for (let j = 0; j < LEAFLET_PAIRS; j++) {
      for (const s of [1, -1]) {
        colour.copy(green).lerp(young, (j / LEAFLET_PAIRS) * 0.6 + Math.random() * 0.15);
        leaflets.setColorAt(k, colour);
        k += 1;
      }
    }
  }
  leaf.add(leaflets);

  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const e = new THREE.Euler();
  const v = new THREE.Vector3();
  const one = new THREE.Vector3(1, 1, 1);
  function layout(t) {
    for (const pin of pinnae) {
      const wave = Math.sin(t * 1.6 + pin.phase);
      pin.pivot.rotation.x = 0.12 * wave;
      pin.pivot.updateMatrixWorld(true);
      const base = pin.pivot.matrix;
      for (let j = 0; j < LEAFLET_PAIRS; j++) {
        const y = 0.012 + (j / (LEAFLET_PAIRS - 1)) * (pin.length - 0.02);
        const size = 0.55 + 0.2 * Math.sin((j / LEAFLET_PAIRS) * Math.PI);
        for (const [n, s] of [[0, 1], [1, -1]]) {
          const flutter = 0.18 * Math.sin(t * 3.2 + j * 0.45 + pin.phase + n);
          e.set(0.35 + flutter, 0, s * (Math.PI / 2 - 0.5) + 0.1 * flutter);
          q.setFromEuler(e);
          v.set(0, y, 0);
          m.compose(v, q, one.clone().multiplyScalar(size));
          m.premultiply(base);
          leaflets.setMatrixAt(pin.first + j * 2 + n, m);
        }
      }
    }
    leaflets.instanceMatrix.needsUpdate = true;
  }

  let visible = true;
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(canvas);
  function resize() {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();
  const clock = new THREE.Timer();
  renderer.setAnimationLoop(() => {
    if (!visible) return;
    clock.update();
    const t = clock.getElapsed();
    leaf.rotation.z = Math.sin(t * 0.7) * 0.06;
    leaf.rotation.x = Math.sin(t * 0.5 + 1) * 0.05;
    layout(t);
    controls.update();
    renderer.render(scene, camera);
  });
}
