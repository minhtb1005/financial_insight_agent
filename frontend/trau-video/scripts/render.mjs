// usage: node scripts/render.mjs M3L2 [--audio]
// Reads public/lessons/<ID>_scenes.json (+ public/audio/<ID>/durations.json if present) and renders out/<ID>.mp4
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const id = process.argv[2];
if (!id) { console.error('lesson id required, e.g. M3L2'); process.exit(1); }
const lesson = JSON.parse(fs.readFileSync(`public/lessons/${id}_scenes.json`, 'utf8'));
const dpath = `public/audio/${id}/durations.json`;
const durations = fs.existsSync(dpath) ? JSON.parse(fs.readFileSync(dpath, 'utf8')) : null;
const open = (lesson.verification || []).filter((v) => v.type === 'placeholder' && v.status === 'open');
if (open.length && !process.argv.includes('--force')) {
  console.error(`REFUSING: ${id} has ${open.length} open placeholder(s) (numbers not filled). Fill them or pass --force for a draft.`);
  for (const v of open) console.error(' -', v.text);
  process.exit(2);
}
const props = {lesson, durations, withAudio: !!durations};
fs.mkdirSync('out', {recursive: true});
fs.writeFileSync(`out/${id}.props.json`, JSON.stringify(props));
const browserArg = process.env.CHROME ? `--browser-executable="${process.env.CHROME}"` : null;
const npx = process.platform === 'win32' ? 'npx.cmd' : 'npx';
execFileSync(npx, ['remotion', 'render', 'src/index.ts', 'Lesson', `out/${id}.mp4`, `--props=out/${id}.props.json`, ...(browserArg ? [browserArg] : [])], {stdio: 'inherit', shell: process.platform === 'win32'});
