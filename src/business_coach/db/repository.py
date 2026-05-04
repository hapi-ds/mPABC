"""Database repository classes for CRUD operations.

Each repository takes a sqlite3.Connection and provides typed methods
for creating, reading, and updating records. Write failures are logged
via the structured logging helpers and re-raised so callers can handle
them.
"""

import logging
import sqlite3
from datetime import datetime, timezone

from business_coach.db.models import ChatMessage, WebSearchResult, Topic, CanvasElement, VoicePersona, PlanSection
from business_coach.logging_config import log_db_error

logger = logging.getLogger(__name__)


def _parse_timestamp(value: str | datetime) -> datetime:
    """Parse a SQLite TIMESTAMP string into a timezone-aware datetime."""
    if isinstance(value, datetime):
        return value
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class TopicRepository:
    """CRUD operations for topics."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, name: str) -> Topic:
        try:
            cursor = self._conn.execute(
                "INSERT INTO topics (name) VALUES (?)",
                (name,),
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT id, name, created_at FROM topics WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            return Topic(
                id=row[0],
                name=row[1],
                created_at=_parse_timestamp(row[2]),
            )
        except sqlite3.Error as exc:
            log_db_error(logger, "INSERT", "topics", str(exc))
            raise

    def get_all(self) -> list[Topic]:
        rows = self._conn.execute(
            "SELECT id, name, created_at FROM topics ORDER BY created_at DESC",
        ).fetchall()
        return [Topic(id=r[0], name=r[1], created_at=_parse_timestamp(r[2])) for r in rows]

    def get_by_id(self, topic_id: int) -> Topic | None:
        row = self._conn.execute(
            "SELECT id, name, created_at FROM topics WHERE id = ?",
            (topic_id,),
        ).fetchone()
        if row is None:
            return None
        return Topic(id=row[0], name=row[1], created_at=_parse_timestamp(row[2]))

    def name_exists(self, name: str) -> bool:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM topics WHERE name = ?",
            (name,),
        ).fetchone()
        return row[0] > 0


class ResearchSessionRepository:
    """CRUD operations for research sessions."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, topic_id: int, query: str) -> int:
        try:
            cursor = self._conn.execute(
                "INSERT INTO research_sessions (topic_id, query) VALUES (?, ?)",
                (topic_id, query),
            )
            self._conn.commit()
            return cursor.lastrowid  # type: ignore
        except sqlite3.Error as exc:
            log_db_error(logger, "INSERT", "research_sessions", str(exc))
            raise

    def get_by_topic(self, topic_id: int) -> list[dict]:
        rows = self._conn.execute(
            """SELECT id, topic_id, query, search_date, status
               FROM research_sessions WHERE topic_id = ?""",
            (topic_id,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "topic_id": r[1],
                "query": r[2],
                "search_date": r[3],
                "status": r[4],
            }
            for r in rows
        ]


class WebSearchRepository:
    """CRUD operations for web search records."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, session_id: int, record: WebSearchResult) -> int:
        try:
            cursor = self._conn.execute(
                """INSERT INTO web_search_results
                   (session_id, url, title, snippet, full_text,
                    source, discovered_date, embedding)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    record.url,
                    record.title,
                    record.snippet,
                    record.full_text,
                    record.source,
                    record.discovered_date.isoformat(),
                    record.embedding,
                ),
            )
            self._conn.commit()
            return cursor.lastrowid  # type: ignore
        except sqlite3.Error as exc:
            log_db_error(logger, "INSERT", "web_search_results", str(exc))
            raise

    def get_by_session(self, session_id: int) -> list[WebSearchResult]:
        rows = self._conn.execute(
            """SELECT id, session_id, url, title, snippet,
                      full_text, source, discovered_date, embedding
               FROM web_search_results WHERE session_id = ?""",
            (session_id,),
        ).fetchall()
        return [
            WebSearchResult(
                id=r[0],
                session_id=r[1],
                url=r[2],
                title=r[3],
                snippet=r[4],
                full_text=r[5],
                source=r[6],
                discovered_date=_parse_timestamp(r[7]),
                embedding=r[8],
            )
            for r in rows
        ]

    def delete(self, result_id: int) -> None:
        try:
            self._conn.execute("DELETE FROM web_search_results WHERE id = ?", (result_id,))
            self._conn.commit()
        except sqlite3.Error as exc:
            log_db_error(logger, "DELETE", "web_search_results", str(exc))
            raise


class ChatHistoryRepository:
    """CRUD operations for chat messages."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save_message(self, topic_id: int, role: str, message: str) -> int:
        try:
            cursor = self._conn.execute(
                "INSERT INTO chat_history (topic_id, role, message) VALUES (?, ?, ?)",
                (topic_id, role, message),
            )
            self._conn.commit()
            return cursor.lastrowid  # type: ignore
        except sqlite3.Error as exc:
            log_db_error(logger, "INSERT", "chat_history", str(exc))
            raise

    def get_by_topic(self, topic_id: int) -> list[ChatMessage]:
        rows = self._conn.execute(
            """SELECT id, topic_id, role, message, timestamp
               FROM chat_history WHERE topic_id = ? ORDER BY timestamp ASC""",
            (topic_id,),
        ).fetchall()
        return [
            ChatMessage(
                id=r[0],
                topic_id=r[1],
                role=r[2],
                message=r[3],
                timestamp=_parse_timestamp(r[4]),
            )
            for r in rows
        ]


class BusinessIdeaRepository:
    """CRUD operations for business ideas."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, topic_id: int, primary_description: str, search_terms: list[str], is_frozen: bool = False) -> int:
        try:
            cursor = self._conn.cursor()
            cursor.execute("BEGIN")

            cursor.execute(
                """INSERT OR REPLACE INTO business_ideas
                   (topic_id, primary_description, is_frozen)
                   VALUES (?, ?, ?)""",
                (topic_id, primary_description, is_frozen),
            )
            idea_id: int = cursor.lastrowid  # type: ignore

            cursor.execute(
                "DELETE FROM idea_search_terms WHERE idea_id = ?",
                (idea_id,),
            )
            for sort_order, term in enumerate(search_terms):
                cursor.execute(
                    """INSERT INTO idea_search_terms
                       (idea_id, term, sort_order)
                       VALUES (?, ?, ?)""",
                    (idea_id, term, sort_order),
                )

            self._conn.commit()
            return idea_id
        except sqlite3.Error as exc:
            self._conn.rollback()
            log_db_error(logger, "UPSERT", "business_ideas", str(exc))
            raise

    def get_by_topic(self, topic_id: int) -> dict | None:
        try:
            row = self._conn.execute(
                """SELECT id, primary_description, is_frozen
                   FROM business_ideas WHERE topic_id = ?""",
                (topic_id,),
            ).fetchone()
            if row is None:
                return None

            idea_id = row[0]
            term_rows = self._conn.execute(
                """SELECT term FROM idea_search_terms
                   WHERE idea_id = ? ORDER BY sort_order ASC""",
                (idea_id,),
            ).fetchall()

            return {
                "id": idea_id,
                "primary_description": row[1],
                "is_frozen": bool(row[2]),
                "search_terms": [r[0] for r in term_rows],
            }
        except sqlite3.Error as exc:
            log_db_error(logger, "SELECT", "business_ideas", str(exc))
            raise


class CanvasElementRepository:
    """CRUD operations for Business Model Canvas elements."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(
        self, topic_id: int, element_name: str, content: str, user_feedback: str | None = None, is_frozen: bool = False
    ) -> None:
        try:
            self._conn.execute(
                """INSERT INTO canvas_elements
                   (topic_id, element_name, content, user_feedback, is_frozen, last_updated)
                   VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(topic_id, element_name) DO UPDATE SET
                   content=excluded.content,
                   user_feedback=excluded.user_feedback,
                   is_frozen=excluded.is_frozen,
                   last_updated=CURRENT_TIMESTAMP""",
                (topic_id, element_name, content, user_feedback, is_frozen),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            log_db_error(logger, "UPSERT", "canvas_elements", str(exc))
            raise

    def get_by_topic(self, topic_id: int) -> list[CanvasElement]:
        rows = self._conn.execute(
            """SELECT id, topic_id, element_name, content, user_feedback, is_frozen, last_updated
               FROM canvas_elements WHERE topic_id = ?""",
            (topic_id,),
        ).fetchall()
        return [
            CanvasElement(
                id=r[0],
                topic_id=r[1],
                element_name=r[2],
                content=r[3],
                user_feedback=r[4],
                is_frozen=bool(r[5]),
                last_updated=_parse_timestamp(r[6]),
            )
            for r in rows
        ]

    def get_element(self, topic_id: int, element_name: str) -> CanvasElement | None:
        row = self._conn.execute(
            """SELECT id, topic_id, element_name, content, user_feedback, is_frozen, last_updated
               FROM canvas_elements WHERE topic_id = ? AND element_name = ?""",
            (topic_id, element_name),
        ).fetchone()
        if row is None:
            return None
        return CanvasElement(
            id=row[0],
            topic_id=row[1],
            element_name=row[2],
            content=row[3],
            user_feedback=row[4],
            is_frozen=bool(row[5]),
            last_updated=_parse_timestamp(row[6]),
        )


class VoicePersonaRepository:
    """CRUD operations for Voice Personas."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, topic_id: int, name: str, description: str, communication_style: str) -> int:
        try:
            cursor = self._conn.execute(
                """INSERT INTO voice_personas
                   (topic_id, name, description, communication_style, last_updated)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (topic_id, name, description, communication_style),
            )
            self._conn.commit()
            return cursor.lastrowid  # type: ignore
        except sqlite3.Error as exc:
            log_db_error(logger, "INSERT", "voice_personas", str(exc))
            raise

    def update(self, persona_id: int, name: str, description: str, communication_style: str) -> None:
        try:
            self._conn.execute(
                """UPDATE voice_personas SET
                   name = ?, description = ?, communication_style = ?, last_updated = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (name, description, communication_style, persona_id),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            log_db_error(logger, "UPDATE", "voice_personas", str(exc))
            raise

    def get_by_topic(self, topic_id: int) -> list[VoicePersona]:
        rows = self._conn.execute(
            """SELECT id, topic_id, name, description, communication_style, last_updated
               FROM voice_personas WHERE topic_id = ?""",
            (topic_id,),
        ).fetchall()
        return [
            VoicePersona(
                id=r[0],
                topic_id=r[1],
                name=r[2],
                description=r[3],
                communication_style=r[4],
                last_updated=_parse_timestamp(r[5]),
            )
            for r in rows
        ]

    def delete_by_topic(self, topic_id: int) -> None:
        try:
            self._conn.execute("DELETE FROM voice_personas WHERE topic_id = ?", (topic_id,))
            self._conn.commit()
        except sqlite3.Error as exc:
            log_db_error(logger, "DELETE", "voice_personas", str(exc))
            raise


class PlanSectionRepository:
    """CRUD operations for Business Plan Sections."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(
        self, topic_id: int, section_name: str, content: str, user_feedback: str | None = None, is_frozen: bool = False
    ) -> None:
        try:
            self._conn.execute(
                """INSERT INTO plan_sections
                   (topic_id, section_name, content, user_feedback, is_frozen, last_updated)
                   VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(topic_id, section_name) DO UPDATE SET
                   content=excluded.content,
                   user_feedback=excluded.user_feedback,
                   is_frozen=excluded.is_frozen,
                   last_updated=CURRENT_TIMESTAMP""",
                (topic_id, section_name, content, user_feedback, is_frozen),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            log_db_error(logger, "UPSERT", "plan_sections", str(exc))
            raise

    def get_by_topic(self, topic_id: int) -> list[PlanSection]:
        rows = self._conn.execute(
            """SELECT id, topic_id, section_name, content, user_feedback, is_frozen, last_updated
               FROM plan_sections WHERE topic_id = ?""",
            (topic_id,),
        ).fetchall()
        return [
            PlanSection(
                id=r[0],
                topic_id=r[1],
                section_name=r[2],
                content=r[3],
                user_feedback=r[4],
                is_frozen=bool(r[5]),
                last_updated=_parse_timestamp(r[6]),
            )
            for r in rows
        ]

    def get_section(self, topic_id: int, section_name: str) -> PlanSection | None:
        row = self._conn.execute(
            """SELECT id, topic_id, section_name, content, user_feedback, is_frozen, last_updated
               FROM plan_sections WHERE topic_id = ? AND section_name = ?""",
            (topic_id, section_name),
        ).fetchone()
        if row is None:
            return None
        return PlanSection(
            id=row[0],
            topic_id=row[1],
            section_name=row[2],
            content=row[3],
            user_feedback=row[4],
            is_frozen=bool(row[5]),
            last_updated=_parse_timestamp(row[6]),
        )


class SourcePreferenceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, topic_id: int, preferences: dict[str, bool]) -> None:
        try:
            cursor = self._conn.cursor()
            cursor.execute("BEGIN")
            cursor.execute("DELETE FROM source_preferences WHERE topic_id = ?", (topic_id,))
            for source_name, enabled in preferences.items():
                cursor.execute(
                    """INSERT INTO source_preferences (topic_id, source_name, enabled)
                       VALUES (?, ?, ?)""",
                    (topic_id, source_name, enabled),
                )
            self._conn.commit()
        except sqlite3.Error as exc:
            self._conn.rollback()
            log_db_error(logger, "REPLACE", "source_preferences", str(exc))
            raise

    def get_by_topic(self, topic_id: int) -> dict[str, bool] | None:
        try:
            rows = self._conn.execute(
                "SELECT source_name, enabled FROM source_preferences WHERE topic_id = ?",
                (topic_id,),
            ).fetchall()
            if not rows:
                return None
            return {r[0]: bool(r[1]) for r in rows}
        except sqlite3.Error as exc:
            log_db_error(logger, "SELECT", "source_preferences", str(exc))
            raise


class WorkflowStepRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(
        self,
        topic_id: int,
        step_key: str,
        content: str,
        status: str,
        personality_mode: str = "critical",
        review_notes: str = "",
    ) -> None:
        try:
            self._conn.execute(
                """INSERT OR REPLACE INTO workflow_steps
                   (topic_id, step_key, content, status, personality_mode,
                    review_notes, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (topic_id, step_key, content, status, personality_mode, review_notes),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            log_db_error(logger, "UPSERT", "workflow_steps", str(exc))
            raise

    def get_step(self, topic_id: int, step_key: str) -> dict | None:
        try:
            row = self._conn.execute(
                """SELECT id, topic_id, step_key, content, status, updated_at,
                          personality_mode, review_notes
                   FROM workflow_steps
                   WHERE topic_id = ? AND step_key = ?""",
                (topic_id, step_key),
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "topic_id": row[1],
                "step_key": row[2],
                "content": row[3],
                "status": row[4],
                "updated_at": row[5],
                "personality_mode": row[6],
                "review_notes": row[7],
            }
        except sqlite3.Error as exc:
            log_db_error(logger, "SELECT", "workflow_steps", str(exc))
            raise


class PersonalityPreferenceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, topic_id: int, preferences: dict[str, str]) -> None:
        try:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM personality_preferences WHERE topic_id = ?", (topic_id,))
            for agent_name, personality_mode in preferences.items():
                cursor.execute(
                    """INSERT INTO personality_preferences (topic_id, agent_name, personality_mode)
                       VALUES (?, ?, ?)""",
                    (topic_id, agent_name, personality_mode),
                )
            self._conn.commit()
        except sqlite3.Error as exc:
            self._conn.rollback()
            log_db_error(logger, "REPLACE", "personality_preferences", str(exc))
            raise

    def get_by_topic(self, topic_id: int) -> dict[str, str] | None:
        try:
            rows = self._conn.execute(
                "SELECT agent_name, personality_mode FROM personality_preferences WHERE topic_id = ?",
                (topic_id,),
            ).fetchall()
            if not rows:
                return None
            return {r[0]: r[1] for r in rows}
        except sqlite3.Error as exc:
            log_db_error(logger, "SELECT", "personality_preferences", str(exc))
            raise


class SpecialistOverrideRepository:
    """CRUD operations for specialist persona overrides."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, topic_id: int, section_name: str, specialist_id: str) -> None:
        """Save or update a specialist override for a section within a topic."""
        try:
            self._conn.execute(
                """INSERT INTO specialist_overrides
                   (topic_id, section_name, specialist_id)
                   VALUES (?, ?, ?)
                   ON CONFLICT(topic_id, section_name) DO UPDATE SET
                   specialist_id=excluded.specialist_id,
                   updated_at=CURRENT_TIMESTAMP""",
                (topic_id, section_name, specialist_id),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            log_db_error(logger, "UPSERT", "specialist_overrides", str(exc))
            raise

    def get_override(self, topic_id: int, section_name: str) -> str | None:
        """Get the specialist override ID for a section, or None if not set."""
        try:
            row = self._conn.execute(
                "SELECT specialist_id FROM specialist_overrides WHERE topic_id = ? AND section_name = ?",
                (topic_id, section_name),
            ).fetchone()
            return row[0] if row else None
        except sqlite3.Error as exc:
            log_db_error(logger, "SELECT", "specialist_overrides", str(exc))
            raise

    def get_all_overrides(self, topic_id: int) -> dict[str, str]:
        """Get all specialist overrides for a topic as {section_name: specialist_id}."""
        try:
            rows = self._conn.execute(
                "SELECT section_name, specialist_id FROM specialist_overrides WHERE topic_id = ?",
                (topic_id,),
            ).fetchall()
            return {r[0]: r[1] for r in rows}
        except sqlite3.Error as exc:
            log_db_error(logger, "SELECT", "specialist_overrides", str(exc))
            raise

    def delete(self, topic_id: int, section_name: str) -> None:
        """Remove a specialist override, reverting to the registry default."""
        try:
            self._conn.execute(
                "DELETE FROM specialist_overrides WHERE topic_id = ? AND section_name = ?",
                (topic_id, section_name),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            log_db_error(logger, "DELETE", "specialist_overrides", str(exc))
            raise
