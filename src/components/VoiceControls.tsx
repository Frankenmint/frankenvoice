import { RotateCcw } from 'lucide-react';
import { useVoiceSettings } from '../VoiceSettingsContext';
import { filterPresets, type FilterPreset } from '../voiceSettings';

const presetLabels: Record<FilterPreset, string> = {
  robot_radio: 'Robot Radio',
  clean: 'Clean',
  telephone: 'Telephone',
  damaged_tape: 'Damaged Tape',
};

export const VoiceControls