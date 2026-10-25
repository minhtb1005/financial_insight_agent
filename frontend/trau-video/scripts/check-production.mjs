import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const course=read(path.join(root,'../src/content/learning-tracks.json'));
const lessons=course.tracks.flatMap(t=>t.modules.flatMap(m=>m.lessons));
assert.equal(new Set(lessons.map(l=>l.id)).size,lessons.length);
const assets=path.join(root,'../public/lesson-videos');
const manifest=fs.existsSync(path.join(assets,'manifest.json'))?read(path.join(assets,'manifest.json')):{lessons:{}};
let ready=0;
for(const item of lessons){
  const lesson=read(path.join(root,'public/lessons',`${item.id}_scenes.json`));
  assert.equal(lesson.lesson_id,item.id);assert.equal(lesson.format.fps,30);
  assert(lesson.scenes.length>=2);
  assert.equal(new Set(lesson.scenes.map(s=>s.id)).size,lesson.scenes.length);
  for(const scene of lesson.scenes){
    assert(scene.vo.text.trim().length>0);
    assert(!/\[\[/.test(JSON.stringify([scene.vo,scene.on_screen_text])),`${item.id}/${scene.id}: placeholder`);
    assert(scene.duration_sec_estimate>0);
  }
  assert(!(lesson.verification||[]).some(v=>v.type==='placeholder'&&v.status==='open'));
  const entry=manifest.lessons[item.id];if(entry?.status!=='ready')continue;
  for(const field of ['src','poster','captions']){
    assert(entry[field].startsWith(`/lesson-videos/${item.id}-`));
    assert(fs.statSync(path.join(assets,path.basename(entry[field]))).size>0);
  }
  const info=JSON.parse(execFileSync('ffprobe',['-v','error','-show_streams','-show_format','-of','json',path.join(assets,entry.filename)],{encoding:'utf8',windowsHide:true}));
  assert(info.streams.some(s=>s.codec_type==='video'&&s.width===1080&&s.height===1920));
  assert(info.streams.some(s=>s.codec_type==='audio'));
  assert(Math.abs(Number(info.format.duration)-entry.duration)<.1);
  const vtt=fs.readFileSync(path.join(assets,path.basename(entry.captions)),'utf8');
  assert(vtt.startsWith('WEBVTT\n\n')&&vtt.includes(' --> '));
  assert.deepEqual(entry.transcript,lesson.scenes.map(s=>s.vo.text));ready++;
}
console.log(JSON.stringify({scriptsChecked:lessons.length,ready,pending:lessons.length-ready},null,2));
if(process.argv.includes('--complete'))assert.equal(ready,lessons.length,'Some videos are not ready');
