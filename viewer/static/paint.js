// Shared by the viewer and the contact-sheet renderer: revealing clumps by _order
// (spec §6.3) and painting the season's two leaf tones across the crown (spec §6.4).

import * as THREE from './vendor/three/three.module.js';
import { foliageTones } from './phenology.js';

const ORDER_CHUNK_VERTEX = '#include <common>\nattribute float _order;\nvarying float vOrder;';
const ORDER_CHUNK_FRAGMENT = '#include <common>\nuniform float uAmount;\nvarying float vOrder;';

const TONE_CHUNK_FRAGMENT = 'uniform vec3 uFrom;\nuniform vec3 uTo;\nuniform float uEdge;\nuniform float uLowest;';
// Two leaf tones across the crown, split by _order with a soft edge (spec §6.4).
const TONE_MIX = `float toneW = smoothstep(uEdge - 0.05, uEdge + 0.05, vOrder);
if (uLowest > 0.5) toneW = 1.0 - toneW;
diffuseColor.rgb = mix(uFrom, uTo, toneW);
#include <map_fragment>`;

// Reveal clumps whose _order is under the part's amount (spec §6.3); with `tone`
// uniforms, also paint the season's two leaf tones (spec §6.4).
export function withOrderReveal(material, uniform, tone = null) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uAmount = uniform;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', ORDER_CHUNK_VERTEX)
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvOrder = _order;');
    let fragment = shader.fragmentShader
      .replace('#include <common>', ORDER_CHUNK_FRAGMENT + (tone ? '\n' + TONE_CHUNK_FRAGMENT : ''))
      .replace('#include <clipping_planes_fragment>', '#include <clipping_planes_fragment>\nif (vOrder > uAmount) discard;');
    if (tone) {
      Object.assign(shader.uniforms, tone);
      fragment = fragment.replace('#include <map_fragment>', TONE_MIX);
    }
    shader.fragmentShader = fragment;
  };
  material.customProgramCacheKey = () => (tone ? 'genes-order-tone' : 'genes-order');
  return material;
}

// The season's two leaf tones as shader uniforms, from the sheet's calendar and the
// look's palette; null when the sheet has no leaf_tones.
export function toneUniforms(palette, sheet, month, amount) {
  const t = foliageTones(sheet, month);
  const tones = palette?.foliage;
  if (!t || !tones || tones.lit) return null;
  const lit = (name) => new THREE.Color((tones[name] ?? tones.mature ?? Object.values(tones)[0]).lit);
  const edge = t.lowest ? amount * t.share : amount * (1 - t.share);
  return {
    uFrom: { value: lit(t.from) },
    uTo: { value: lit(t.to) },
    uEdge: { value: t.share > 0 ? edge : 2.0 },
    uLowest: { value: t.lowest ? 1 : 0 },
  };
}
