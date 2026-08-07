"""
mitchell.core.memory
====================
High-level memory facade (Phase 3) over the SQLite three-store backend
(``mitchell.core.memory_store``).

Keeps the legacy function names the planner calls (get_user_profile,
get_skills_log, find_cached_plan, ...) so nothing upstream breaks, while the
actual persistence is the structured episodic / semantic / procedural store.

Exposed capabilities:
  * Episodic  : log_episode / list_episodes  (append-only ground truth)
  * Semantic  : remember_semantic / recall_semantic / all_semantic
  * Procedural: save_schema* / retrieve_schema (retrieved before a task)
  * Learning  : promote_verified_patterns    (verified episodes -> skill doc)
"""
from __future__ import annotations

from mitchell.core import memory_store as ms


# ---- legacy / planner-compatible API --------------------------------------

def get_user_profile() -> str:
    return ms.get_semantic("user_profile") or ""


def update_user_profile(insights: str):
    current = get_user_profile()
    merged = (current + f"\n- {insights}").strip()
    ms.update_semantic("user_profile", merged)


def get_skills_log() -> str:
    return ms.get_semantic("skills_log") or ""


def log_skill(skill_name: str, purpose: str):
    current = get_skills_log()
    merged = (current + f"\n- {skill_name}: {purpose}").strip()
    ms.update_semantic("skills_log", merged)


def save_task_pattern(instruction: str, steps: list[dict]):
    ms.save_task_pattern(instruction, steps, success_rate=1.0)


def find_cached_plan(instruction: str, threshold: int = 85) -> list[dict] | None:
    return ms.find_cached_plan(instruction, threshold=threshold)


# ---- episodic --------------------------------------------------------------

def log_episode(task_id, kind, summary, verified=False, pattern_key=None, data=None) -> int:
    return ms.log_episode(task_id, kind, summary, verified=verified, pattern_key=pattern_key, data=data)


def list_episodes(kind=None, verified=None, limit=100) -> list[dict]:
    return ms.list_episodes(kind=kind, verified=verified, limit=limit)


# ---- semantic --------------------------------------------------------------

def remember_semantic(key: str, value: str):
    """Record a world fact. When reality changes, the old value is replaced."""
    ms.update_semantic(key, value)


def recall_semantic(key: str) -> str | None:
    return ms.get_semantic(key)


def all_semantic() -> dict[str, str]:
    return ms.all_semantic()


# ---- procedural ------------------------------------------------------------

def save_schema(title: str, body: str, source_task=None, verified=True) -> int:
    """Persist a procedural skill doc (usually the RESULT of promotion)."""
    return ms.save_procedural(title, body, source_task=source_task, verified=verified)


def retrieve_schema(instruction: str, threshold: int = 45) -> dict | None:
    """Retrieve the best verified skill doc for an instruction, or None."""
    return ms.retrieve_procedural(instruction, threshold=threshold)


def list_schemas(verified=None) -> list[dict]:
    return ms.list_procedural(verified=verified)


# ---- learning mechanic -----------------------------------------------------

def promote_verified_patterns(min_occurrences: int = 2) -> list[str]:
    """Promote verified episodic clusters into procedural skill docs.

    Gated on Phase 1 verification by construction: no unverified episode is
    ever promoted.
    """
    return ms.promote_verified_patterns(min_occurrences=min_occurrences, insist_verified=True)
