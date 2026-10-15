export type OnScreen = {text: string; split_hint?: string[]; position?: string};
export type Scene = {
  id: string;
  duration_sec_estimate: number;
  visual: {description: string; mascot_pose: string | null; characters: string[]};
  vo: {text: string; word_count: number};
  on_screen_text: OnScreen[];
};
export type Lesson = {
  lesson_id: string;
  title: string;
  module_title?: string;
  scenes: Scene[];
  end_card: {duration_sec: number; on_screen_text: string[]};
  format: {width: number; height: number; fps: number};
};
// seconds per scene measured from real TTS audio (optional)
export type Durations = {voice?: string; scenes: Record<string, number>};
export type Props = {lesson: Lesson; durations: Durations | null; withAudio: boolean};
