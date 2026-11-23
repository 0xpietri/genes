// Compresses one genes model in place of a copy (spec §8): meshopt geometry
// (EXT_meshopt_compression) and nothing else. Textures are already WebP from
// Blender's exporter. Scene extras and the _ORDER attribute are kept.
//
//   node tools/compress/compress.mjs in.glb out.glb
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { meshopt, dedup } from '@gltf-transform/functions';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error('usage: node compress.mjs in.glb out.glb');
  process.exit(2);
}
await MeshoptEncoder.ready;
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(input);
// The generator name is fixed so the same model gives the same bytes.
doc.getRoot().getAsset().generator = 'genes plant generator (Blender, gltf-transform)';
await doc.transform(dedup(), meshopt({ encoder: MeshoptEncoder, level: 'medium' }));
await io.write(output, doc);
