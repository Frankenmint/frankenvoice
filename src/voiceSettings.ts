export const filterPresets = [
  'robot_radio',
  'clean',
  'telephone',
  'damaged_tape',
] as const;

export type FilterPreset = (typeof filterPresets)[number];

export interface VoiceSettings {
  filterPreset: FilterPreset;
  variation: number;
  sourceDiversity: number;
  pauseLength: number;
  glitch: number;
}

export const defaultVoiceSettings: VoiceSettings = {
  filterPreset: 'telephone',
  variation: 50,
  sourceDiversity: 50,
  pauseLength: 50,
  glitch: 0,
};
