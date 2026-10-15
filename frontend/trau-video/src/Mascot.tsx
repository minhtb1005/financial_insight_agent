import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {TrauSvg} from './trau/Trau';


// Scene JSON `mascot_pose` values map to drawn poses (happy|think|point|wave|idle).
export const Mascot: React.FC<{pose: string | null; size?: number}> = ({pose, size = 400}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12}});
  const bob = Math.sin(frame / 10) * 6;
  const tilt = pose === 'think' ? -3 : pose === 'celebrate' ? Math.sin(frame / 5) * 4 : pose === 'wave' ? Math.sin(frame / 6) * 2 : 0;
  const p = (pose ?? 'idle') as any;
  const S = TrauSvg;
  return (
    <div style={{transform: `translateY(${bob}px) rotate(${tilt}deg) scale(${interpolate(pop, [0, 1], [0.6, 1])})`}}>
      <S pose={p} size={size} />
    </div>
  );
};
