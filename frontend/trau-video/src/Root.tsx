import React from 'react';
import {Composition} from 'remotion';
import {Lesson, totalFrames} from './Lesson';
import type {Props} from './types';
import {TrauPoseStill, TrauSheet} from './TrauStill';
import demo from '../public/lessons/M3L2_scenes.json';

const defaults: Props = {lesson: demo as unknown as Props['lesson'], durations: null, withAudio: false};

export const Root: React.FC = () => (
  <>
  <Composition id="TrauSheet" component={TrauSheet} width={2200} height={560} fps={30} durationInFrames={1} />
  <Composition id="TrauPose" component={TrauPoseStill} width={1040} height={820} fps={30} durationInFrames={1} defaultProps={{pose: 'happy' as const}} />
  <Composition
    id="Lesson"
    component={Lesson}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={totalFrames(defaults)}
    defaultProps={defaults}
    calculateMetadata={({props}) => ({durationInFrames: totalFrames(props as Props), fps: (props as Props).lesson.format.fps})}
  />
  </>
);
