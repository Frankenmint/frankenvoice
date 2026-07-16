import sqlite3
import os
import hashlib
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.getcwd(), "data", "metadata.sqlite")

def get_connection():
    """Get a connection with WAL mode enabled for concurrency"""
    conn = sqlite3.connect(DB_PATH, isolation_level=None) # Auto-commit
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
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
    c.execute('''CREATE TABLE IF NOT EXISTS voices (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    filter_preset TEXT DEFAULT 'robot_radio',
    source_tags TEXT -- Comma separated tags to filter sources
)''')
    conn.commit()
    conn.close()

    
def get_clip_path_hash(word: str, source_id: int, start_time: float) -> str:
    """Generate a safe subdirectory path to avoid inode limits"""
    unique_string = f"{word}_{source_id}_{start_time}"
    hash_obj = hashlib.md5(unique_string.encode())
    hash_hex = hash_obj.hexdigest()
    # Use first 2 chars for subdir, rest for filename
    return os.path.join(hash_hex[:2], hash_hex[2:])

def add_clip(clip_data: Dict):
    conn = get_connection()
    c = conn.cursor()
    
    # Generate safe path
    rel_path = get_clip_path_hash(clip_data['word'], clip_data['source_id'], clip_data['start'])
    full_dir = os.path.join(os.getcwd(), "data", "dataset", "clips", rel_path.split('/')[0])
    os.makedirs(full_dir, exist_ok=True)
    
    # Update path in data
    clip_data['path'] = os.path.join("data", "dataset", "clips", rel_path + ".wav")

    c.execute('''INSERT INTO clips 
        (word, normalized_word, source_id, start_time, end_time, file_path, confidence, duration_ms, pitch_hz, loudness_lufs, context_before, context_after)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (clip_data['word'], clip_data['normalized_word'], clip_data['source_id'],
         clip_data['start'], clip_data['end'], clip_data['path'],
         clip_data['confidence'], clip_data['duration'], clip_data.get('pitch'),
         clip_data.get('loudness'), clip_data.get('ctx_before'), clip_data.get('ctx_after')))
    
    conn.close()

def get_clips_for_word(word: str, limit: int = 50) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    # Search exact match or normalized
    c.execute("SELECT * FROM clips WHERE normalized_word = ? AND disabled = 0 ORDER BY RANDOM() LIMIT ?", (word.lower(), limit))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM clips")
    total_clips = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT normalized_word) FROM clips")
    unique_words = c.fetchone()[0]
    conn.close()
    return {"total_clips": total_clips, "unique_words": unique_words}
