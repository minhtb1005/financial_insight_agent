// Resume-safe pipeline. Publishes only validated videos, then atomically updates the manifest.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn, execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderMedia} from '@remotion/renderer';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root);
const out=path.join(root,'out');
const assets=path.resolve(root,'../public/lesson-videos');
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(assets,{recursive:true});
const manifestPath=path.join(assets,'manifest.json');
const statePath=path.join(out,'batch-status.json');
const lock=path.join(out,'batch.lock');
try{fs.writeFileSync(lock,String(process.pid),{flag:'wx'});}catch{throw Error('Batch lock exists. Check out/batch.lock PID before restarting.');}
process.on('exit',()=>{try{fs.unlinkSync(lock);}catch{}});
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const write=(p,data)=>{fs.writeFileSync(p+'.tmp',JSON.stringify(data,null,2)+'\n');fs.renameSync(p+'.tmp',p);};
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
const course=read('../src/content/learning-tracks.json');
const lessons=course.tracks.flatMap(t=>t.modules.flatMap(m=>m.lessons.map(l=>({...l,track:t.id}))));
const requested=process.argv.find(a=>a.startsWith('--ids='))?.slice(6).split(',');
const voice=process.argv.find(a=>a.startsWith('--voice='))?.slice(8)||'vi-VN-NamMinhNeural';
const manifest=fs.existsSync(manifestPath)?read(manifestPath):{version:1,lessons:{}};
for(const l of lessons)manifest.lessons[l.id]??={status:'pending',title:l.title,track:l.track};
const state={startedAt:new Date().toISOString(),pid:process.pid,status:'running',current:null,completed:[],failed:{}};
const update=()=>{state.updatedAt=new Date().toISOString();write(statePath,state);};
write(manifestPath,manifest);update();
const run=(command,args)=>new Promise((resolve,reject)=>{
  const child=spawn(command,args,{cwd:root,windowsHide:true,stdio:'inherit'});
  child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(Error(`${command} exited ${code}`)));
});
const probe=file=>{
  const info=JSON.parse(execFileSync('ffprobe',['-v','error','-show_streams','-show_format','-of','json',file],{encoding:'utf8',windowsHide:true}));
  const video=info.streams.find(s=>s.codec_type==='video');
  if(!video||video.width!==1080||video.height!==1920||!info.streams.some(s=>s.codec_type==='audio')||Number(info.format.duration)<=3)throw Error(`Invalid video: ${file}`);
  return info;
};
const stamp=seconds=>new Date(Math.round(seconds*1000)).toISOString().slice(11,23);
function captions(props){
  let offset=0;const cues=[];
  for(const s of props.lesson.scenes){
    const seconds=Math.max(Math.round((props.durations.scenes[s.id]+.35)*30),15)/30;
    const words=s.vo.text.split(/\s+/);const chunks=[];
    for(let i=0;i<words.length;i+=9)chunks.push(words.slice(i,i+9).join(' '));
    const clock=Math.max(seconds-.4,1/30);
    chunks.forEach((chunk,i)=>cues.push(`${stamp(offset+i*clock/chunks.length)} --> ${stamp(offset+(i===chunks.length-1?seconds:(i+1)*clock/chunks.length))}\n${chunk}`));
    offset+=seconds;
  }
  return 'WEBVTT\n\n'+cues.join('\n\n')+'\n';
}
let browser,serveUrl;
const browserExecutable=process.env.CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe';
const rendererHash=hash(fs.readdirSync('src').filter(f=>/\.tsx?$/.test(f)).sort().map(f=>fs.readFileSync(path.join('src',f))).join('')+fs.readFileSync('src/trau/Trau.tsx'));
try{
  for(const item of lessons.filter(l=>!requested||requested.includes(l.id))){
    const id=item.id;
    state.current={lessonId:id,stage:'audio',progress:0};update();
    try{
      const lesson=read(`public/lessons/${id}_scenes.json`);
      if(lesson.scenes.some(s=>/\[\[/.test(JSON.stringify([s.vo,s.on_screen_text]))))throw Error('Unresolved script');
      const signature=hash(JSON.stringify(lesson)+rendererHash+(id==='M1L1'?'approved':voice));
      const cached=manifest.lessons[id];
      if(cached.status==='ready'&&cached.signature===signature&&fs.existsSync(path.join(assets,cached.filename))){probe(path.join(assets,cached.filename));state.completed.push(id);update();continue;}
      const approved='out/M1L1-review-20261022.mp4';
      const reuse=id==='M1L1'&&fs.existsSync(approved)&&read('out/M1L1-review-20261022.props.json').lesson.scenes.every((s,i)=>s.vo.text===lesson.scenes[i]?.vo.text&&JSON.stringify(s.on_screen_text)===JSON.stringify(lesson.scenes[i]?.on_screen_text));
      if(!reuse)await run(process.env.VIDEO_PYTHON||'python',['scripts/tts.py',id,voice]);
      const durations=read(`public/audio/${id}/durations.json`);
      if(lesson.scenes.some(s=>!Number.isFinite(durations.scenes[s.id])||durations.scenes[s.id]<=0))throw Error('Incomplete audio');
      const props={lesson,durations,withAudio:true};
      const filename=`${id}-${signature.slice(0,12)}.mp4`;
      const target=path.join(assets,filename);
      const intermediate=path.join(out,`${id}.pending.mp4`);
      state.current={lessonId:id,stage:'render',progress:0};update();
      if(reuse)fs.copyFileSync(approved,intermediate);
      else{
        if(!serveUrl)serveUrl=await bundle({entryPoint:path.join(root,'src/index.ts'),publicDir:path.join(root,'public')});
        const bundledAudio=path.join(serveUrl,'public/audio',id);
        fs.mkdirSync(bundledAudio,{recursive:true});fs.cpSync(path.join(root,'public/audio',id),bundledAudio,{recursive:true});
        browser??=await openBrowser('chrome',{browserExecutable});
        const composition=await selectComposition({serveUrl,id:'Lesson',inputProps:props,puppeteerInstance:browser,browserExecutable});
        let last=-1;
        await renderMedia({serveUrl,composition,inputProps:props,codec:'h264',outputLocation:intermediate,puppeteerInstance:browser,browserExecutable,concurrency:4,crf:20,x264Preset:'veryfast',onProgress:({progress})=>{
          const percent=Math.floor(progress*100);if(percent!==last){last=percent;state.current.progress=percent;update();console.log(`${id}: ${percent}%`);}
        }});
      }
      const info=probe(intermediate);
      const expected=lesson.scenes.reduce((n,s)=>n+Math.max(Math.round((durations.scenes[s.id]+.35)*30),15),0)/30+lesson.end_card.duration_sec;
      if(Math.abs(Number(info.format.duration)-expected)>.2)throw Error('Duration mismatch');
      const poster=filename.replace('.mp4','.jpg');
      execFileSync('ffmpeg',['-y','-v','error','-ss','2','-i',intermediate,'-frames:v','1','-update','1',path.join(assets,poster)],{windowsHide:true});
      const vtt=filename.replace('.mp4','.vtt');fs.writeFileSync(path.join(assets,vtt),captions(props));
      fs.copyFileSync(intermediate,target+'.tmp');fs.renameSync(target+'.tmp',target);
      manifest.lessons[id]={status:'ready',title:item.title,track:item.track,filename,signature,src:`/lesson-videos/${filename}`,poster:`/lesson-videos/${poster}`,captions:`/lesson-videos/${vtt}`,duration:Number(info.format.duration),voice:durations.voice,sources:lesson.sources||[],transcript:lesson.scenes.map(s=>s.vo.text),updatedAt:new Date().toISOString()};
      write(manifestPath,manifest);state.completed.push(id);update();console.log(`PUBLISHED ${id}`);
    }catch(error){state.failed[id]=String(error);console.error(`FAILED ${id}:`,error);update();}
  }
  state.status=Object.keys(state.failed).length?'completed_with_errors':'completed';state.current=null;update();
}finally{await browser?.close({silent:true});}
