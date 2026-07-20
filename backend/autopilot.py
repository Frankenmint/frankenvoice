import json
import uuid
from pathlib import Path
from typing import Any

from backend import db, engine
from backend.enrichment import coverage_for_text, enrich_missing_words, tokenize
from backend.qwen_cloud import QwenCloudError, plan_autopilot_workflow
from backend.speech_service import generate_composite_speech

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "data" / "aut