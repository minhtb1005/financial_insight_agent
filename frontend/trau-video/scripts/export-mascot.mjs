// Exports assets/trau/trau_<pose>.svg (vector) via react-dom/server, and PNGs via `remotion still` (transparent).
import fs from 'node:fs';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {build} from 'esbuild';
import * as JSX from 'react/jsx-runtime';
const out = await build({entryPoints: [process.argv[2] || 'src/trau/Trau.tsx'], bundle: true, format: 'cjs', write: false, external: ['react', 'react/jsx-runtime'], jsx: 'automatic'});
const m = {exports: {}}; new Function('module', 'exports', 'require', out.outputFiles[0].text)(m, m.exports, (k) => (k === 'react' ? React : k === 'react/jsx-runtime' ? JSX : null));
const XuSvg = m.exports.XuSvg || m.exports.TrauSvg; const NAME = process.argv[3] || 'trau';
fs.mkdirSync(`assets/${NAME}`, {recursive: true});
for (const pose of ['happy', 'think', 'point', 'wave', 'idle']) {
  fs.writeFileSync(`assets/${NAME}/${NAME}_${pose}.svg`, renderToStaticMarkup(React.createElement(XuSvg, {pose, size: 400})).replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" '));
}
console.log('svg done');
