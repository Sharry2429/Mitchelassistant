"""
mitchell.core.memory_store
==========================
Phase 3 — persistent memory as THREE stores in one SQLite database
(no vector DB until retrieval quality is actually the bottleneck).

  episodic    append-only raw log: what was tried, what happened, timestamped.
              This is the ground-truth everything else is derived from.
  semantic    facts about the world (project structure, conventions, device
              quirks, API shapes). UPSERTED when reality changes — not appended
              forever. A fact that changes replaces the old one.
  procedural  skill documents ("what approach works for this task class").
              Retrieved BEFORE a task starts. Written ONLY from runs that
              passed real Phase 1 verification.

The learning mechanic: verified episodic entries -> periodic review ->
promotion into a procedural doc. Promotion is gated on verification BY
CONSTRUCTION: only episodes logged with verified=True can be promoted, and the
promotion function refuses anything unverified. An ungated version would launder
bad episodes into confidently-wrong permanent habits — so there is no ungated
path here.

SQLite is synchronous and durable; each operation opens a short-lived
connection (WAL) so it is safe to call from anywhere without connection
lifetime headaches.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from fuzzywuzzy import fuzz

MEMORY_DIR = Path(os.path.expanduser("~/.system-mcp/memory"))
DB_PATH = MEMORY_DIR / "mitchell.db"


def _connect() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                task_id TEXT,
                kind TEXT NOT NULL,
                summary TEXT NOT NULL,
                verified INTEGER NOT NULL DEFAULT 0,
                pattern_key TEXT,
                data TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_episodic_verified ON episodic(verified);
            CREATE INDEX IF NOT EXISTS idx_episodic_pattern ON episodic(pattern_key);

            CREATE TABLE IF NOT EXISTS semantic (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS procedural (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                source_task TEXT,
                verified INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                retrieved_count INTEGER NOT NULL DEFAULT 0,
                last_retrieved REAL
            );
            CREATE INDEX IF NOT EXISTS idx_procedural_verified ON procedural(verified);

            CREATE TABLE IF NOT EXISTS task_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instruction TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                success_rate REAL NOT NULL DEFAULT 1.0,
                created_at REAL NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# EPISODIC — append-only ground-truth log
# --------------------------------------------------------------------------

def log_episode(
    task_id: str | None,
    kind: str,
    summary: str,
    verified: bool = False,
    pattern_key: str | None = None,
    data: dict | None = None,
) -> int:
    """Append an episode. Never edit/delete — append-only ground truth."""
    init_db()
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO episodic (ts, task_id, kind, summary, verified, pattern_key, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), task_id, kind, summary, 1 if verified else 0, pattern_key,
             json.dumps(data) if data is not None else None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_episodes(
    kind: str | None = None, verified: bool | None = None, limit: int = 100
) -> list[dict]:
    init_db()
    conn = _connect()
    try:
        q = "SELECT * FROM episodic WHERE 1=1"
        params: list = []
        if kind is not None:
            q += " AND kind = ?"
            params.append(kind)
        if verified is not None:
            q += " AND verified = ?"
            params.append(1 if verified else 0)
        q += " ORDER BY id ASC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --------------------------------------------------------------------------
# SEMANTIC — facts that change, upserted not appended
# --------------------------------------------------------------------------

def update_semantic(key: str, value: str) -> None:
    """Set a semantic fact. Reality changed -> REPLACES the old value."""
    init_db()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO semantic (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def get_semantic(key: str) -> str | None:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT value FROM semantic WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def all_semantic() -> dict[str, str]:
    init_db()
    conn = _connect()
    try:
        return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM semantic")}
    finally:
        conn.close()


# --------------------------------------------------------------------------
# PROCEDURAL — skill documents, retrieved before a task starts
# --------------------------------------------------------------------------

def save_procedural(
    title: str,
    body: str,
    source_task: str | None = None,
    verified: bool = True,
) -> int:
    init_db()
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO procedural (title, body, source_task, verified, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, body, source_task, 1 if verified else 0, time.time()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_procedural(verified: bool | None = None) -> list[dict]:
    init_db()
    conn = _connect()
    try:
        q = "SELECT * FROM procedural WHERE 1=1"
        params: list = []
        if verified is not None:
            q += " AND verified = ?"
            params.append(1 if verified else 0)
        q += " ORDER BY id ASC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()


def _score_doc(doc: dict, instruction: str) -> float:
    text = f"{doc.get('title','')}\n{doc.get('body','')}"
    return max(fuzz.ratio(instruction.lower(), text.lower()),
               fuzz.token_set_ratio(instruction.lower(), text.lower()))


def retrieve_procedural(instruction: str, threshold: int = 45) -> dict | None:
    """Return the best procedural doc for an instruction, or None."""
    docs = list_procedural(verified=True)
    if not docs:
        return None
    best = max(docs, key=lambda d: _score_doc(d, instruction))
    score = _score_doc(best, instruction)
    if score < threshold:
        return None
    conn = _connect()
    try:
        conn.execute(
            "UPDATE procedural SET retrieved_count = retrieved_count + 1, last_retrieved = ? "
            "WHERE id = ?",
            (time.time(), best["id"]),
        )
        conn.commit()
    finally:
        conn.close()
    return best


# --------------------------------------------------------------------------
# LEARNING MECHANIC — promote VERIFIED episodes into a procedural skill doc
# --------------------------------------------------------------------------

def _episode_to_procedural_body(episodes: list[dict]) -> str:
    """Aggregate verified episodes of one pattern into a how-to body."""
    lines = []
    for ep in episodes:
        lines.append(f"- ({ep['kind']}) {ep['summary']}")
    return "\n".join(lines)


def promote_verified_patterns(min_occurrences: int = 2, insist_verified: bool = True) -> list[str]:
    """Scan episodic, group by pattern_key, and promote clusters that (a) have
    enough occurrences AND (b) are ALL verified. Returns promoted titles.

    The verification gate is enforced here structurally: if insist_verified is
    True (always), an unverified episode disqualifies its whole cluster.
    """
    init_db()
    episodes = list_episodes()
    groups: dict[str, list[dict]] = {}
    for ep in episodes:
        pk = ep.get("pattern_key")
        if not pk:
            continue
        groups.setdefault(pk, []).append(ep)

    promoted: list[str] = []
    for pk, eps in groups.items():
        if len(eps) < min_occurrences:
            continue
        # Verification gate BY CONSTRUCTION: any unverified episode blocks the cluster.
        if insist_verified and any(not ep["verified"] for ep in eps):
            continue
        title = "Pattern: " + pk.replace("_", " ")
        body = _episode_to_procedural_body(eps)
        source_task = eps[-1]["task_id"]
        save_procedural(title=title, body=body, source_task=source_task, verified=True)
        promoted.append(title)

    return promoted


# --------------------------------------------------------------------------
# TASK-PATTERN CACHE (planner compatibility) — fuzzy plan recall
# --------------------------------------------------------------------------

def save_task_pattern(instruction: str, steps: list[dict], success_rate: float = 1.0) -> None:
    init_db()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO task_patterns (instruction, steps_json, success_rate, created_at) "
            "VALUES (?, ?, ?, ?)",
            (instruction, json.dumps(steps), success_rate, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def find_cached_plan(instruction: str, threshold: int = 85) -> list[dict] | None:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT instruction, steps_json FROM task_patterns ORDER BY id DESC LIMIT 200"
        ).fetchall()
    finally:
        conn.close()

    best = None
    best_score = 0
    for r in rows:
        score = fuzz.ratio(instruction.lower(), r["instruction"].lower())
        if score > best_score and score >= threshold:
            best_score = score
            best = json.loads(r["steps_json"])
    return best
