import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {TrauSvg} from './trau/Trau';


// Scene JSON `mascot_pose` values map to drawn poses (happy|think|point|wave|idle).
// energy/mouthOpen come from VO amplitude (0 when silent); stills omit them (= calm pose).
export const Mascot: React.FC<{pose: string | null; size?: number; energy?: number; mouthOpen?: number}> = ({pose, size = 400, energy = 0, mouthOpen = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const e = Math.min(1, Math.max(0, energy));
  const pop = spring({frame, fps, config: {damping: 12}});
  const bob = Math.sin(frame / 10) * (6 + 8 * e) - Math.abs(Math.sin(frame / 4)) * 14 * e;
  const baseTilt = pose === 'think' ? -3 : pose === 'celebrate' ? Math.sin(frame / 5) * 4 : pose === 'wave' ? Math.sin(frame / 6) * 2 : 0;
  const tilt = baseTilt * (1 + 1.5 * e) + Math.sin(frame / 7) * 2 * e;
  const p = (pose ?? 'idle') as any;
  const S = TrauSvg;
  return (
    <div style={{transform: `translateY(${bob}px) rotate(${tilt}deg) scale(${interpolate(pop, [0, 1], [0.6, 1])})`}}>
      <S pose={p} size={size} mouthOpen={mouthOpen} />
    </div>
  );
};
