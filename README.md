# ⚡ FrankenVoice ⚡

### *Look through the noise. Hear the voice inside it.*

**Local-first composite speech synthesis built from real recorded words.**

![frankenvoice audio stereogram](https://github.com/Frankenmint/frankenvoice/blob/main/assets/hero.jpeg?raw=true)  

🕒 Average time to solve the hidden image: ~30 seconds  


# What is FrankenVoice?  

FrankenVoice reconstructs speech from **real recorded audio** instead of generating it from scratch.

Feed it long-form recordings—interviews, podcasts, YouTube videos, speeches—and it:

- 🎙️ Transcribes every spoken word
- 🔎 Builds a searchable database of clips
- 🧩 Finds matching words across every recording
- ⚡ Stitches real human recordings into entirely new sentences
- 🎛️ Applies a unified effects chain so every fragment sounds like one transmission

The result feels less like traditional TTS and more like intercepting a transmission assembled from thousands of recovered voice fragments.

---

# Demo Workflow

1. Paste a YouTube URL.
2. FrankenVoice downloads audio.
3. Whisper transcribes every word.
4. Every spoken word becomes an indexed audio fragment.
5. Type anything.
6. FrankenVoice searches its database.
7. Matching clips are assembled.
8. A shared audio filter creates one cohesive synthetic voice.

```
YouTube
    │
    ▼
Audio Extraction
    │
    ▼
Whisper Transcription
    │
    ▼
Word Database
    │
    ▼
Clip Selection
    │
    ▼
Audio Stitching
    │
    ▼
Shared Filter Chain
    │
    ▼
FrankenVoice
```

# Setup

This application requires:

- Node.js
- Python
- SQLite

## Frontend

```bash
npm create vite@latest frankenvoice-ui -- --template react-ts
npm install tailwindcss postcss autoprefixer wavesurfer.js axios lucide-react clsx tailwind-merge
```

## Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

---

# Current WIP

- Phoneme fallback via espeak-ng
- Prosody matching with pitch contour analysis
- OpenAI-compatible TTS API
- Improved clip ranking
- Voice dataset management
- Additional transmission effects