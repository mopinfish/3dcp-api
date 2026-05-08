/**
 * ply_to_spz.mjs — PLY → SPZ 変換スクリプト（Task 6 ローカル変換用）
 * 使い方: node ply_to_spz.mjs <input.ply> <output.spz>
 */
import { createReadStream, readFileSync, writeFileSync } from 'fs';
import { Readable } from 'stream';
import { loadPly, serializeSpz } from 'spz-js';

const [,, inputPly, outputSpz] = process.argv;
if (!inputPly || !outputSpz) {
  console.error('Usage: node ply_to_spz.mjs <input.ply> <output.spz>');
  process.exit(1);
}

console.log(`Loading PLY: ${inputPly}`);
const fileStream = createReadStream(inputPly);
const webStream = Readable.toWeb(fileStream);
const gs = await loadPly(webStream);
console.log(`Loaded ${gs.numPoints} gaussians`);

console.log('Serializing to SPZ...');
const spzData = await serializeSpz(gs);
writeFileSync(outputSpz, Buffer.from(spzData));
console.log(`Written SPZ: ${outputSpz} (${spzData.byteLength.toLocaleString()} bytes)`);
