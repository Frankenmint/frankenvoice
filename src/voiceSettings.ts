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

export const presetSettings: Record<FilterPreset, VoiceSettings> = {
  clean: {
    filterPreset: 'clean',
    variation: 20,
    sourceDiversity: 20,
    pauseLength: 30,
    glitch: 0,
  },
  robot_radio: {
    filterPreset: 'robot_radio',
    variation: 60,
    sourceDiversity: 70,
    pauseLength: 45,
    glitch: 12,
  },
  telephone: {
    filterPreset: 'telephone',
    variation: 35,
    sourceDiversity: 40,
    pauseLength: 35,
    glitch: 0,
  },
  damaged_tape: {
    filterPreset: 'damaged_tape',
    variation: 85,
    sourceDiversity: 90,
    pauseLength: 65,
    glitch: 55,
  },
};

export const defaultVoiceSettings: VoiceSettings = presetSettings.robot_radio;
