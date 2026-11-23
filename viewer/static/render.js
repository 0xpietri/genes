// One model, one camera, one picture: what `genes contact-sheet` captures (spec §7.1).
//   /render.html?model=<glb url>&view=side|front|back|left|below|above&mode=painted|silhouette
//                &month=1..12&sheet=<sheet url>&look=<look url> (its leaf tones)
//                &w=640&h=640&parts=bark,fruit (only those)
//                &person=1 (a 1.75 m person beside it) &frame=<metres> (a fixed square
//                frame standing on the ground, so several models share one scale)
// The camera stands at eye height (1.6 m) like a person taking a photo, far enough to
// fit the whole model. body[data-ready] is set when the frame is drawn.

import * as THREE from './vendor/three/three.module.js';
import { GLTFLoader } from './vendor/three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from './vendor/three/addons/libs/meshopt_decoder.module.js';
import { partAmounts } from './phenology.js';
import { withOrderReveal, toneUniforms } from './paint.js';

const q = new URLSearchParams(location.search);
const W = Number(q.get('w') ?? 640);
const H = Number(q.get('h') ?? 640);
const mode = q.get('mode') ?? 'painted';
const view = q.get('view') ?? 'side';
const month = Number(q.get('month') ?? 1);
const frame = Number(q.get('frame') ?? 0);
const PERSON_HEIGHT_M = 1.75;

function toonGradient() {
  const tex = new THREE.DataTexture(new Uint8Array([90, 170, 255]), 3, 1, THREE.RedFormat);
  tex.minFilter = tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
}

async function main() {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H);
  document.body.append(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(mode === 'silhouette' ? 0xffffff : 0xdfe8ee);
  scene.add(new THREE.AmbientLight(0xffffff, 1.2));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(4, 8, 6);
  scene.add(sun);

  let amounts = { foliage: 1, flowers: 0, fruit: 0 };
  let sheet = null;
  if (q.get('sheet')) {
    sheet = await (await fetch(q.get('sheet'))).json();
    amounts = partAmounts(sheet, month);
  }
  const look = q.get('look') ? await (await fetch(q.get('look'))).json() : null;
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const gltf = await loader.loadAsync(q.get('model'));
  const root = gltf.scene;
  const gradient = toonGradient();
  root.traverse((obj) => {
    if (!obj.isMesh) return;
    const base = obj.material;
    const part = base.name || obj.name;
    let mat;
    if (mode === 'silhouette') {
      mat = new THREE.MeshBasicMaterial({ color: 0x000000, map: base.map, alphaTest: base.alphaTest });
    } else {
      mat = new THREE.MeshToonMaterial({ color: base.color, map: base.map, alphaTest: base.alphaTest, gradientMap: gradient });
    }
    mat.side = THREE.DoubleSide;
    if (part in amounts) {
      obj.visible = amounts[part] > 0;
      const tone = mode === 'painted' && part === 'foliage' && look
        ? toneUniforms(look.palette, sheet, month, amounts.foliage) : null;
      if (tone) mat.color.set(0xffffff);
      if (obj.geometry.getAttribute('_order')) withOrderReveal(mat, { value: amounts[part] }, tone);
    }
    obj.material = mat;
    if (q.get('parts') && !q.get('parts').split(',').includes(part)) obj.visible = false;
  });
  scene.add(root);

  const box = new THREE.Box3().setFromObject(root);
  if (q.get('person') === '1') {
    const person = new THREE.Mesh(
      new THREE.CapsuleGeometry(0.2, PERSON_HEIGHT_M - 0.4, 6, 12),
      mode === 'silhouette'
        ? new THREE.MeshBasicMaterial({ color: 0x000000 })
        : new THREE.MeshToonMaterial({ color: 0x5b6c8a, gradientMap: gradient }),
    );
    person.position.set(box.max.x + 0.6, PERSON_HEIGHT_M / 2, 0);
    scene.add(person);
    box.expandByObject(person);
  }
  if (frame > 0) {
    // A fixed frame: the same metres per pixel whatever the model.
    box.set(new THREE.Vector3(-frame / 2, 0, -frame / 2), new THREE.Vector3(frame / 2, frame, frame / 2));
  }
  const size = box.getSize(new THREE.Vector3());
  const centre = box.getCenter(new THREE.Vector3());
  const fov = 35;
  const camera = new THREE.PerspectiveCamera(fov, W / H, 0.05, 500);
  const extent = Math.max(size.y, size.x, size.z) * 1.15;
  const dist = extent / 2 / Math.tan(THREE.MathUtils.degToRad(fov / 2)) + Math.max(size.x, size.z) / 2;
  const eye = Math.min(1.6, size.y * 0.5);
  const dirs = {
    side: new THREE.Vector3(0, 0, 1),
    front: new THREE.Vector3(1, 0, 0),
    back: new THREE.Vector3(0, 0, -1),
    left: new THREE.Vector3(-1, 0, 0),
    below: new THREE.Vector3(0, 0, 1),
    above: new THREE.Vector3(0.0, 1.4, 1),
  };
  const dir = (dirs[view] ?? dirs.side).normalize();
  if (view === 'close') {
    // Near the crown's edge, at eye height: flowers, pods and the clump texture.
    const edge = new THREE.Vector3(centre.x, Math.min(size.y * 0.45, 3), box.max.z);
    camera.position.set(edge.x + size.x * 0.12, 1.6, edge.z + Math.max(size.y * 0.35, 1.2));
    camera.lookAt(edge);
  } else if (view === 'below') {
    camera.position.set(centre.x, 1.2, centre.z + Math.max(size.x, size.z) * 0.15);
    camera.lookAt(centre.x, size.y, centre.z - size.z * 0.1);
  } else {
    camera.position.copy(centre).addScaledVector(dir, dist);
    if (view !== 'above') camera.position.y = eye;
    camera.lookAt(centre);
  }
  renderer.render(scene, camera);
  document.body.dataset.ready = '1';
}

main().catch((err) => {
  document.body.dataset.error = String(err);
  console.error(err);
});
