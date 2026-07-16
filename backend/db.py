import sqlite3
import os
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.getcwd(), "data", "metadata.sqlite")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Sources Table
    c.execute('''CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        source_type TEXT, -- 'youtube', 'local_file'
        file_path TEXT,
        status TEXT DEFAULT 'pending', -- pending, processing, complete, failed
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Clips Table (The Core Dataset)
    c.execute('''CREATE TABLE IF NOT EXISTS clips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        normalized_word TEXT NOT NULL,
        source_id INTEGER,
        start_time REAL,
        end_time REAL,
        file_path TEXT,
        confidence REAL,
        duration_ms REAL,
        pitch_hz REAL,
        loudness_lufs REAL,
        context_before TEXT,
        context_after TEXT,
        rating INTEGER DEFAULT 0,
        disabled BOOLEAN DEFAULT 0,
        FOREIGN KEY(source_id) REFERENCES sources(id)
    )''')
    
    # Create indices for fast search
    c.execute('CREATE INDEX IF NOT EXISTS idx_word ON clips(normalized_word)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_source ON clips(source_id)')
    
    conn.commit()
    conn.close()

def add_clip(clip_data: Dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO clips 
        (word, normalized_word, source_id, start_time, end_time, file_path, confidence, duration_ms, pitch_hz, loudness_lufs, context_before, context_after)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (clip_data['word'], clip_data['normalized_word'], clip_data['source_id'],
         clip_data['start'], clip_data['end'], clip_data['path'],
         clip_data['confidence'], clip_data['duration'], clip_data.get('pitch'),
         clip_data.get('loudness'), clip_data.get('ctx_before'), clip_data.get('ctx_after')))
    conn.commit()
    conn.close()

def get_clips_for_word(word: str, limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Search exact match or normalized
    c.execute("SELECT * FROM clips WHERE normalized_word = ? AND disabled = 0 ORDER BY RANDOM() LIMIT ?", (word.lower(), limit))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM clips")
    total_clips = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT normalized_word) FROM clips")
    unique_words = c.fetchone()[0]
    conn.close()
    return {"total_clips": total_clips, "unique_words": unique_words}
