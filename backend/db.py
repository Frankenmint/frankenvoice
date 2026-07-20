import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "metadata.sqlite"
DERIVED_SOURCE_TITLE = "Qwen Derived Corpus"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, name: str, ddl: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                source_type TEXT,
                file_path TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS clips (
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
            );

            CREATE INDEX IF NOT EXISTS idx_word ON clips(normalized_word);
            CREATE INDEX IF NOT EXISTS idx_source ON clips(source_id);

            CREATE TABLE IF NOT EXISTS voices (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                filter_preset TEXT DEFAULT 'robot_radio',
                source_tags TEXT
            );
            """
        )
        _ensure_column(conn, "sources", "qwen_voice_id", "TEXT")
        _ensure_column(conn, "sources", "transcription_provider", "TEXT")
        _ensure_column(conn, "clips", "provenance", "TEXT DEFAULT 'original'")
        _ensure_column(conn, "clips", "voice_profile_id", "TEXT")


def create_source(
    title: str,
    source_type: str,
    file_path: str,
    status: str = "pending",
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sources (title, source_type, file_path, status)
            VALUES (?, ?, ?, ?)
            """,
            (title, source_type, file_path, status),
        )
        return int(cursor.lastrowid)


def get_or_create_derived_source() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM sources WHERE title = ? AND source_type = 'qwen_derived'",
            (DERIVED_SOURCE_TITLE,),
        ).fetchone()
        if row:
            return int(row["id"])
        cursor = conn.execute(
            """
            INSERT INTO sources (title, source_type, file_path, status, transcription_provider)
            VALUES (?, 'qwen_derived', '', 'complete', 'qwen_tts')
            """,
            (DERIVED_SOURCE_TITLE,),
        )
        return int(cursor.lastrowid)


def update_source_status(source_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE sources SET status = ? WHERE id = ?", (status, source_id))


def set_source_voice_profile(source_id: int, voice_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE sources SET qwen_voice_id = ? WHERE id = ?", (voice_id, source_id)
        )


def set_source_transcription_provider(source_id: int, provider: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE sources SET transcription_provider = ? WHERE id = ?",
            (provider, source_id),
        )


def get_source(source_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    return dict(row) if row else None


def get_source_progress(source_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT s.*, COUNT(c.id) AS clip_count
            FROM sources s
            LEFT JOIN clips c ON c.source_id = s.id
            WHERE s.id = ?
            GROUP BY s.id
            """,
            (source_id,),
        ).fetchone()
    return dict(row) if row else None


def get_clip_path_hash(word: str, source_id: int, start_time: float) -> str:
    unique_string = f"{word}_{source_id}_{start_time}"
    hash_hex = hashlib.md5(unique_string.encode(), usedforsecurity=False).hexdigest()
    return str(Path(hash_hex[:2]) / hash_hex[2:])


def add_clip(clip_data: Dict) -> int:
    rel_path = get_clip_path_hash(
        clip_data["word"], clip_data["source_id"], clip_data["start"]
    )
    canonical_path = Path("data") / "dataset" / "clips" / f"{rel_path}.wav"
    (PROJECT_ROOT / canonical_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO clips (
                word, normalized_word, source_id, start_time, end_time,
                file_path, confidence, duration_ms, pitch_hz, loudness_lufs,
                context_before, context_after, provenance, voice_profile_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clip_data["word"],
                clip_data["normalized_word"],
                clip_data["source_id"],
                clip_data["start"],
                clip_data["end"],
                str(canonical_path),
                clip_data.get("confidence", 1.0),
                clip_data["duration"],
                clip_data.get("pitch"),
                clip_data.get("loudness"),
                clip_data.get("ctx_before"),
                clip_data.get("ctx_after"),
                clip_data.get("provenance", "original"),
                clip_data.get("voice_profile_id"),
            ),
        )
        return int(cursor.lastrowid)


def get_clips_for_word(word: str, limit: int = 50) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM clips
            WHERE normalized_word = ? AND disabled = 0
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (word.lower(), limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_word_counts(words: List[str]) -> Dict[str, int]:
    normalized = sorted({word.lower() for word in words if word.strip()})
    if not normalized:
        return {}
    placeholders = ",".join("?" for _ in normalized)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT normalized_word, COUNT(*) AS clip_count
            FROM clips
            WHERE disabled = 0 AND normalized_word IN ({placeholders})
            GROUP BY normalized_word
            """,
            normalized,
        ).fetchall()
    counts = {word: 0 for word in normalized}
    counts.update({row["normalized_word"]: int(row["clip_count"]) for row in rows})
    return counts


def get_stats() -> Dict[str, int]:
    with get_connection() as conn:
        total_clips = conn.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
        unique_words = conn.execute(
            "SELECT COUNT(DISTINCT normalized_word) FROM clips"
        ).fetchone()[0]
        derived_clips = conn.execute(
            "SELECT COUNT(*) FROM clips WHERE provenance = 'qwen_derived'"
        ).fetchone()[0]
    return {
        "total_clips": total_clips,
        "unique_words": unique_words,
        "derived_clips": derived_clips,
    }
