# frankenvoice
Qwen3 Hackathon Submission


frankenvoice/
├── backend/
│   ├── app.py                  # FastAPI Entry Point
│   ├── engine.py               # Core Logic (Ingestion, Transcription, Synthesis)
│   ├── db.py                   # SQLite & Metadata Management
│   ├── audio_utils.py          # FFmpeg/Librosa wrappers
│   ├── filters.py              # Audio Filter Chains (Robot, Radio, etc.)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── SourceManager.tsx
│   │   │   ├── Composer.tsx       # Center Panel
│   │   │   ├── WordBlock.tsx      # Individual Editable Token
│   │   │   ├── DatasetInspector.tsx
│   │   │   └── VoiceControls.tsx  # Right Panel
│   │   ├── hooks/
│   │   │   └── useAudioPlayer.ts
│   │   └── api.ts
│   └── package.json
└── data/                     # Shared volume for clips/db
    ├── dataset/
    ├── sources/
    └── metadata.sqlite
