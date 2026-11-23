// Day and night around the tree: a gradient dome, a sun among drifting clouds by day, a moon
// and twinkling stars by night. Textures are drawn on canvases here, so nothing is downloaded.

import * as THREE from '/static/vendor/three/three.module.js';

const DAY = {
  top: new THREE.Color('#5d9bd0'), horizon: new THREE.Color('#d6e7ee'), bottom: new THREE.Color('#c9c59a'),
  hemiSky: new THREE.Color('#e3eef8'), hemiGround: new THREE.Color('#8f8460'), hemi: 1.35,
  key: new THREE.Color('#fff0d4'), keyI: 2.4, ground: new THREE.Color('#a2a66e'),
};
const NIGHT = {
  top: new THREE.Color('#02040c'), horizon: new THREE.Color('#16223d'), bottom: new THREE.Color('#0d1320'),
  hemiSky: new THREE.Color('#5a6f9c'), hemiGround: new THREE.Color('#1a1f26'), hemi: 0.75,
  key: new THREE.Color('#b9c9ff'), keyI: 0.9, ground: new THREE.Color('#3a4434'),
};
const SUN_DIR = new THREE.Vector3(0.55, 0.62, 0.55).normalize();
const MOON_DIR = new THREE.Vector3(-0.5, 0.58, 0.64).normalize();

function canvasTexture(size, draw) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  draw(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function glow(colourIn, colourOut, core) {
  return canvasTexture(256, (g, s) => {
    const r = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    r.addColorStop(0, colourIn);
    r.addColorStop(core, colourIn);
    r.addColorStop(core + 0.04, colourOut);
    r.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = r;
    g.fillRect(0, 0, s, s);
  });
}

function moonTexture() {
  return canvasTexture(256, (g, s) => {
    const halo = g.createRadialGradient(s / 2, s / 2, s * 0.16, s / 2, s / 2, s / 2);
    halo.addColorStop(0, 'rgba(220,230,255,0.45)');
    halo.addColorStop(1, 'rgba(220,230,255,0)');
    g.fillStyle = halo;
    g.fillRect(0, 0, s, s);
    g.beginPath();
    g.arc(s / 2, s / 2, s * 0.17, 0, Math.PI * 2);
    g.fillStyle = '#eef1f6';
    g.fill();
    g.save();
    g.clip();
    for (const [x, y, r, a] of [[-0.05, -0.04, 0.05, 0.16], [0.06, 0.03, 0.035, 0.14], [-0.02, 0.08, 0.03, 0.12],
      [0.07, -0.07, 0.025, 0.1], [-0.09, 0.04, 0.02, 0.1]]) {
      g.beginPath();
      g.arc(s / 2 + x * s, s / 2 + y * s, r * s, 0, Math.PI * 2);
      g.fillStyle = `rgba(120,130,150,${a})`;
      g.fill();
    }
    g.restore();
  });
}

function cloudTexture(seed) {
  let x = seed * 9301 + 49297;
  const rnd = () => ((x = (x * 9301 + 49297) % 233280) / 233280);
  return canvasTexture(256, (g, s) => {
    g.filter = 'blur(6px)';
    for (let k = 0; k < 16; k++) {
      const cx = s * (0.2 + rnd() * 0.6);
      const cy = s * (0.45 + (rnd() - 0.5) * 0.25);
      const r = s * (0.08 + rnd() * 0.12);
      const grad = g.createRadialGradient(cx, cy - r * 0.3, 0, cx, cy, r);
      grad.addColorStop(0, 'rgba(255,255,255,0.95)');
      grad.addColorStop(0.7, 'rgba(244,247,250,0.7)');
      grad.addColorStop(1, 'rgba(230,236,242,0)');
      g.fillStyle = grad;
      g.beginPath();
      g.arc(cx, cy, r, 0, Math.PI * 2);
      g.fill();
    }
  });
}

export class Sky {
  constructor(scene, renderer) {
    this.scene = scene;
    this.renderer = renderer;
    this.blend = 0; // 0 day, 1 night
    this.target = 0;

    this.dome = new THREE.Mesh(
      new THREE.SphereGeometry(450, 32, 16),
      new THREE.ShaderMaterial({
        side: THREE.BackSide, depthWrite: false, fog: false,
        uniforms: { top: { value: DAY.top.clone() }, horizon: { value: DAY.horizon.clone() }, bottom: { value: DAY.bottom.clone() } },
        vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
        fragmentShader: `uniform vec3 top; uniform vec3 horizon; uniform vec3 bottom; varying vec3 vP;
          void main(){ float h = vP.y; vec3 c = h > 0.0 ? mix(horizon, top, pow(smoothstep(0.0, 0.85, h), 0.7)) : mix(horizon, bottom, smoothstep(0.0, 0.12, -h));
          gl_FragColor = vec4(c, 1.0); }`,
      }),
    );
    this.dome.renderOrder = -10;
    scene.add(this.dome);

    this.hemi = new THREE.HemisphereLight(DAY.hemiSky, DAY.hemiGround, DAY.hemi);
    scene.add(this.hemi);
    this.key = new THREE.DirectionalLight(DAY.key, DAY.keyI);
    scene.add(this.key);
    scene.fog = new THREE.Fog(DAY.horizon.clone(), 90, 420);

    const sprite = (map, size, dir, dist) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false, fog: false }));
      s.scale.set(size, size, 1);
      s.position.copy(dir).multiplyScalar(dist);
      s.renderOrder = -5;
      scene.add(s);
      return s;
    };
    this.sun = sprite(glow('rgba(255,251,230,1)', 'rgba(255,226,160,0.35)', 0.12), 120, SUN_DIR, 380);
    this.moon = sprite(moonTexture(), 70, MOON_DIR, 380);

    this.clouds = new THREE.Group();
    const textures = [1, 2, 3, 4].map(cloudTexture);
    for (let k = 0; k < 18; k++) {
      const m = new THREE.SpriteMaterial({ map: textures[k % 4], transparent: true, depthWrite: false, fog: false, opacity: 0.9 });
      const s = new THREE.Sprite(m);
      const a = (k / 18) * Math.PI * 2 + Math.sin(k * 7.3) * 0.3;
      const r = 230 + (k % 5) * 30;
      s.position.set(Math.cos(a) * r, 55 + ((k * 37) % 90), Math.sin(a) * r);
      const w = 90 + ((k * 53) % 70);
      s.scale.set(w, w * 0.5, 1);
      s.renderOrder = -4;
      this.clouds.add(s);
    }
    scene.add(this.clouds);

    const n = 1600;
    const pos = new Float32Array(n * 3);
    const seed = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const u = Math.random();
      const th = Math.random() * Math.PI * 2;
      const y = 0.05 + u * 0.95;
      const rr = Math.sqrt(1 - y * y);
      pos.set([Math.cos(th) * rr * 420, y * 420, Math.sin(th) * rr * 420], i * 3);
      seed[i] = Math.random();
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('seed', new THREE.BufferAttribute(seed, 1));
    this.starMat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: false, blending: THREE.AdditiveBlending,
      uniforms: { time: { value: 0 }, opacity: { value: 0 }, scale: { value: renderer.getPixelRatio() } },
      vertexShader: `attribute float seed; uniform float time; uniform float scale; varying float vA;
        void main(){ vA = 0.55 + 0.45 * sin(time * (0.8 + seed * 2.2) + seed * 40.0);
        gl_PointSize = (1.0 + seed * seed * 2.6) * scale; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `uniform float opacity; varying float vA;
        void main(){ vec2 d = gl_PointCoord - 0.5; float a = smoothstep(0.5, 0.0, length(d));
        gl_FragColor = vec4(vec3(0.92, 0.95, 1.0), a * vA * opacity); }`,
    });
    this.stars = new THREE.Points(g, this.starMat);
    this.stars.renderOrder = -6;
    scene.add(this.stars);
    this.apply();
  }

  setNight(night, instant = false) {
    this.target = night ? 1 : 0;
    if (instant) { this.blend = this.target; this.apply(); }
  }

  /** The ground's colour now (the stage paints its disc with it). */
  groundColour(out) {
    return out.copy(DAY.ground).lerp(NIGHT.ground, this.blend);
  }

  apply() {
    const b = this.blend;
    const u = this.dome.material.uniforms;
    u.top.value.copy(DAY.top).lerp(NIGHT.top, b);
    u.horizon.value.copy(DAY.horizon).lerp(NIGHT.horizon, b);
    u.bottom.value.copy(DAY.bottom).lerp(NIGHT.bottom, b);
    this.scene.fog.color.copy(u.horizon.value);
    this.hemi.color.copy(DAY.hemiSky).lerp(NIGHT.hemiSky, b);
    this.hemi.groundColor.copy(DAY.hemiGround).lerp(NIGHT.hemiGround, b);
    this.hemi.intensity = THREE.MathUtils.lerp(DAY.hemi, NIGHT.hemi, b);
    this.key.color.copy(DAY.key).lerp(NIGHT.key, b);
    this.key.intensity = THREE.MathUtils.lerp(DAY.keyI, NIGHT.keyI, b);
    this.key.position.copy(b < 0.5 ? SUN_DIR : MOON_DIR).multiplyScalar(30);
    this.sun.material.opacity = 1 - b;
    this.sun.visible = b < 0.99;
    this.moon.material.opacity = b;
    this.moon.visible = b > 0.01;
    this.starMat.uniforms.opacity.value = Math.max(0, b * 1.3 - 0.3);
    const cloud = new THREE.Color('#ffffff').lerp(new THREE.Color('#3a4560'), b);
    for (const c of this.clouds.children) {
      c.material.color.copy(cloud);
      c.material.opacity = 0.9 - b * 0.55;
    }
  }

  update(dt, t) {
    if (this.blend !== this.target) {
      const step = dt / 1.4;
      this.blend = this.blend < this.target ? Math.min(this.target, this.blend + step) : Math.max(this.target, this.blend - step);
      this.apply();
    }
    this.clouds.rotation.y = t * 0.004;
    this.starMat.uniforms.time.value = t;
  }
}
