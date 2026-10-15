import React from 'react';
import {AbsoluteFill, Series} from 'remotion';
import {SceneView} from './SceneView';
import {C, FONT} from './theme';
import type {Props} from './types';

export const sceneFrames = (p: Props, id: string, est: number, fps: number) => {
  const real = p.durations?.scenes?.[id];
  return Math.max(Math.round(((real ?? est) + (real ? 0.35 : 0)) * fps), 15);
};

export const totalFrames = (p: Props) => {
  const fps = p.lesson.format.fps;
  return p.lesson.scenes.reduce((a, s) => a + sceneFrames(p, s.id, s.duration_sec_estimate, fps), 0) + Math.round(p.lesson.end_card.duration_sec * fps);
};

export const Lesson: React.FC<Props> = (p) => {
  const fps = p.lesson.format.fps;
  return (
    <AbsoluteFill>
      <Series>
        {p.lesson.scenes.map((s) => {
          const f = sceneFrames(p, s.id, s.duration_sec_estimate, fps);
          return (
            <Series.Sequence key={s.id} durationInFrames={f}>
              <SceneView scene={s} lessonId={p.lesson.lesson_id} withAudio={p.withAudio} total={f} />
            </Series.Sequence>
          );
        })}
        <Series.Sequence durationInFrames={Math.round(p.lesson.end_card.duration_sec * fps)}>
          <AbsoluteFill style={{background: C.ink, color: '#fff', fontFamily: FONT, justifyContent: 'center', alignItems: 'center', padding: 80, textAlign: 'center', fontSize: 52, lineHeight: 1.4}}>
            {p.lesson.end_card.on_screen_text.join(' ')}
          </AbsoluteFill>
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
