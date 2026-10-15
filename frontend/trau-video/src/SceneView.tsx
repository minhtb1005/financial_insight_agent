import React from 'react';
import {AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Mascot} from './Mascot';
import {C, FONT} from './theme';
import type {Scene} from './types';

const chunk = (text: string, n = 9) => {
  const w = text.split(/\s+/).filter(Boolean);
  const out: string[] = [];
  for (let i = 0; i < w.length; i += n) out.push(w.slice(i, i + n).join(' '));
  return out.length ? out : [''];
};

export const SceneView: React.FC<{scene: Scene; lessonId: string; withAudio: boolean; total: number}> = ({scene, lessonId, withAudio, total}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  // on-screen items: split "A · B · C" into stacked cards that appear in sequence
  const parts = scene.on_screen_text.flatMap((o) => o.split_hint ?? [o.text]).filter((t) => !t.includes('Số liệu minh họa'));
  const showMinhHoa = scene.on_screen_text.some((o) => o.text.includes('Số liệu minh họa'));
  const subs = chunk(scene.vo.text);
  const subIdx = Math.min(subs.length - 1, Math.floor((frame / Math.max(total - fps * 0.4, 1)) * subs.length));
  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: FONT, color: C.ink}}>
      {withAudio && <Audio src={staticFile(`audio/${lessonId}/${scene.id}.mp3`)} />}
      <div style={{position: 'absolute', top: 120, width: '100%', display: 'flex', justifyContent: 'center'}}>
        <Mascot pose={scene.visual.mascot_pose} />
      </div>
      <div style={{position: 'absolute', top: 560, left: 60, right: 60, display: 'flex', flexDirection: 'column', gap: 24}}>
        {parts.map((t, i) => {
          const s = spring({frame: frame - 10 - i * 14, fps, config: {damping: 14}});
          return (
            <div key={i} style={{background: C.card, borderRadius: 28, padding: '28px 36px', fontSize: 58, fontWeight: 700, lineHeight: 1.2,
              boxShadow: '0 8px 0 ' + C.ink, border: `4px solid ${C.ink}`, opacity: s, transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px)`}}>
              {t.replace(/\[\[[^\]]*\]\]/g, '— (chờ số liệu) —')}
            </div>
          );
        })}
      </div>
      <div style={{position: 'absolute', bottom: 150, left: 70, right: 70, textAlign: 'center', fontSize: 50, fontWeight: 600, lineHeight: 1.3,
        background: 'rgba(31,42,68,0.88)', color: '#fff', borderRadius: 24, padding: '24px 30px'}}>
        {subs[subIdx]}
      </div>
      {showMinhHoa && <div style={{position: 'absolute', left: 40, bottom: 60, fontSize: 34, opacity: 0.75}}>Số liệu minh họa</div>}
    </AbsoluteFill>
  );
};
