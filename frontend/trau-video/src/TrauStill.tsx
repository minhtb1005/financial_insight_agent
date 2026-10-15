import React from 'react';
import {AbsoluteFill} from 'remotion';
import {TrauSvg, TrauPose} from './trau/Trau';

export const TrauPoseStill: React.FC<{pose: TrauPose}> = ({pose}) => (
  <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}><TrauSvg pose={pose} size={780} /></AbsoluteFill>
);
export const TrauSheet: React.FC = () => (
  <AbsoluteFill style={{background: '#FFF7E8', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around'}}>
    {(['idle', 'happy', 'think', 'point', 'wave'] as TrauPose[]).map((p) => <TrauSvg key={p} pose={p} size={420} />)}
  </AbsoluteFill>
);
