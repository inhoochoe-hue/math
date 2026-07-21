from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS source_problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    source_number INTEGER,
    problem_text TEXT NOT NULL,
    analysis_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS generated_problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    unit TEXT,
    concept TEXT,
    difficulty TEXT,
    question_type TEXT,
    question TEXT NOT NULL,
    choices_json TEXT,
    answer TEXT,
    solution TEXT,
    quality_json TEXT,
    approved INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES source_problems(id)
);
"""


class ProblemBank:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_source(self, source_file: str, source_number: int, text: str, analysis: dict[str, Any]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO source_problems(source_file, source_number, problem_text, analysis_json) VALUES (?, ?, ?, ?)",
                (source_file, source_number, text, json.dumps(analysis, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def add_variant(self, source_id: int, analysis: dict[str, Any], item: dict[str, Any], quality: dict[str, Any]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """INSERT INTO generated_problems(
                    source_id, unit, concept, difficulty, question_type, question,
                    choices_json, answer, solution, quality_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source_id,
                    analysis.get("unit", ""),
                    analysis.get("concept", ""),
                    item.get("difficulty", ""),
                    item.get("question_type", ""),
                    item.get("question", ""),
                    json.dumps(item.get("choices", []), ensure_ascii=False),
                    item.get("answer", ""),
                    item.get("solution", ""),
                    json.dumps(quality, ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid)

    def list_variants(self, limit: int = 500) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM generated_problems ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
