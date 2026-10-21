import React from 'react';
import {AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {getWaveformPortion, useAudioData} from '@remotion/media-utils';
import {Board, BOARD} from './Board';
import {Mascot} from './Mascot';
import {C, FONT} from './theme';
import type {Scene} from './types';

const chunk = (text: string, n = 9) => {
  const w = text.split(/\s+/).filter(Boolean);
  const out: string[] = [];
  for (let i = 0; i < w.length; i += n) out.push(w.slice(i, i + n).join(' '));
  return out.length ? out : [''];
};

// Mascot box: svg height = size; feet ellipse bottom sits at 0.9022*size below the top.
const MASCOT_SIZE = 460;
const MASCOT_FEET = 1545;

export const SceneView: React.FC<{scene: Scene; lessonId: string; withAudio: boolean; total: number; isFirst?: boolean}> = ({scene, lessonId, withAudio, total, isFirst = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  // Lip-sync: VO amplitude drives mouth + body. Unconditional hook (Series.Sequence
  // already reset frame to scene-local, matching the per-scene Audio below). Null-safe:
  // audioData null (stills / missing file) -> energy 0, renders exactly as before.
  const audioData = useAudioData(staticFile(`audio/${lessonId}/${scene.id}.mp3`));
  const audioFrames = audioData ? Math.floor(audioData.durationInSeconds * fps) : 0;
  let energy = 0;
  let mouthOpen = 0;
  if (audioData && frame < audioFrames) {
    const avg = (bars: {amplitude: number}[]) => bars.reduce((x, y) => x + y.amplitude, 0) / Math.max(bars.length, 1);
    const wStart = Math.max(frame - 10, 0); // ~0.7s window ~= EMA smooth for body
    const wide = getWaveformPortion({audioData, startTimeInSeconds: wStart / fps, durationInSeconds: Math.min(21, audioFrames - wStart) / fps, numberOfSamples: 64});
    energy = Math.min(1, avg(wide) * 6);
    const near = getWaveformPortion({audioData, startTimeInSeconds: frame / fps, durationInSeconds: Math.min(3, audioFrames - frame) / fps, numberOfSamples: 16});
    mouthOpen = Math.min(1, Math.max(0, (avg(near) - 0.015) * 8));
  }
  // on-screen items: split "A · B · C" into chalk lines that appear in sequence
  const parts = scene.on_screen_text.flatMap((o) => o.split_hint ?? [o.text]).filter((t) => !t.includes('Số liệu minh họa'));
  const showMinhHoa = scene.on_screen_text.some((o) => o.text.includes('Số liệu minh họa'));
  const subs = chunk(scene.vo.text);
  const subClock = Math.max(total - fps * 0.4, 1);
  const subIdx = Math.min(subs.length - 1, Math.floor((frame / subClock) * subs.length));
  const n = parts.length;
  // Same clock as the subtitle; guard n=0 (S8) -> no active line, no pulse.
  const lineIdx = n === 0 ? -1 : Math.min(Math.max(n - 1, 0), Math.floor((subIdx * n) / subs.length));
  // First frame at which floor(subIdx*n/subs.length) reaches i (same clock as the subtitle).
  const lineStarts = parts.map((_, i) => Math.ceil((Math.ceil((i * subs.length) / n) * subClock) / subs.length));

  // Pulse `point` only when the base pose has nothing sustained to say.
  const basePose = scene.visual.mascot_pose;
  const canPulse = basePose === null || basePose === 'idle' || basePose === 'happy';
  const pulseStart = lineIdx >= 0 ? Math.max(lineStarts[lineIdx], isFirst ? 34 : 10) : Infinity;
  const pulseAge = frame - pulseStart;
  const pulsing = canPulse && n > 0 && pulseAge >= 0 && pulseAge < 24;
  const walkingIn = isFirst && frame < 30;
  const pose = walkingIn ? 'wave' : pulsing ? 'point' : basePose;

  // Arm raise: static -35 for base `point`; pulses aim at the active line (higher line = higher arm).
  const fontSize = n <= 3 ? 58 : n === 4 ? 52 : 44;
  const gap = n >= 4 ? 16 : 24;
  const lineH = fontSize * 1.3;
  const blockH = n * lineH + Math.max(n - 1, 0) * gap;
  const lineY = BOARD.y + BOARD.h / 2 - blockH / 2 + Math.max(lineIdx, 0) * (lineH + gap) + lineH / 2;
  const aimDeg = Math.max(-60, Math.min(-20, -20 - ((BOARD.y + BOARD.h - lineY) / BOARD.h) * 40));
  const pointDeg = basePose === 'point' ? -35 : pulsing ? aimDeg : 0;

  const walk = spring({frame, fps, config: {damping: 200}, durationInFrames: 40});
  const walkX = isFirst ? interpolate(walk, [0, 1], [-620, 0]) : 0;
  const mascotTop = MASCOT_FEET - MASCOT_SIZE * 0.9022;

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: FONT, color: C.ink}}>
      {withAudio && <Audio src={staticFile(`audio/${lessonId}/${scene.id}.mp3`)} />}
      <Board parts={parts} lineIdx={lineIdx} lineStarts={lineStarts} />
      <div style={{position: 'absolute', left: 30, top: mascotTop, transform: `translateX(${walkX}px)`}}>
        <Mascot pose={pose} size={MASCOT_SIZE} energy={energy} mouthOpen={mouthOpen} pointDeg={pointDeg} />
      </div>
      <div style={{position: 'absolute', bottom: 150, left: 70, right: 70, textAlign: 'center', fontSize: 50, fontWeight: 600, lineHeight: 1.3,
        background: 'rgba(31,42,68,0.88)', color: '#fff', borderRadius: 24, padding: '24px 30px'}}>
        {subs[subIdx]}
      </div>
      {showMinhHoa && <div style={{position: 'absolute', right: 40, bottom: 60, fontSize: 34, opacity: 0.75}}>Số liệu minh họa</div>}
    </AbsoluteFill>
  );
};
