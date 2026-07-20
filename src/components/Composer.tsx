import { useEffect, useState } from 'react';
import axios from 'axios';
import { CloudCog, Download, Play, RefreshCw, Sparkles } from 'lucide-react';
import {
  API_BASE,
  getCoverage,
  getProviderStatus,
  type CoverageResult,
  type ProviderStatus,
} from '../api';
import { useVoiceSettings } from '../VoiceSettingsContext';

export const Composer = () => {
  const { settings } = useVoiceSettings();