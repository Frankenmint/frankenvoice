# frankenvoice
Qwen3 Hackathon Submission

# Setup
this app requires node and python and sqlite pre-requisites.

run the following commands:

```
npm create vite@latest frankenvoice-ui -- --template react-ts 
npm install tailwindcss postcss autoprefixer wavesurfer.js axios lucide-react clsx tailwind-merge
```


# How to Run the Demo  

Backend:  
```
cd backend  
pip install -r requirements.txt  
python app.py  
```
Frontend:  
```
cd frontend  
npm install  
npm run dev  
```
Workflow:  

1. Go to Left Panel, paste a YouTube URL (e.g., a long interview).  
1. Wait for processing (check terminal logs).  
1. Go to Center Panel, type: "I am trying to reach you."  
1. Click GENERATE TRANSMISSION.  
1. Listen to the stitched, filtered result.  
1. Toggle "Robot Radio" filter off/on in Right Panel to hear the difference.  

# WIP Expansion  

1. Phoneme Fallback: Integrate espeak-ng to generate missing words phonetically instead of silence.  
1. Prosody Matching: Analyze pitch contour of surrounding words and pitch-shift the selected clip to match (using librosa.effects.pitch_shift).  
1. TTS API Compatibility: Wrap the /generate endpoint to accept OpenAI-compatible JSON requests, allowing FrankenVoice to be dropped into any app that supports standard TTS APIs.  


# Folder layout structure
```
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
```