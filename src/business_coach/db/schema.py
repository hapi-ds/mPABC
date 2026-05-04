"""SQLite schema initialization and database connection factory.

Defines the CREATE TABLE statements for the business coach database and
provides a connection factory that initializes the schema on first use.
"""

import sqlite3
from pathlib import Path

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS web_search_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    snippet TEXT,
    full_text TEXT,
    source TEXT NOT NULL DEFAULT 'web',
    discovered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding BLOB,
    FOREIGN KEY (session_id) REFERENCES research_sessions(id)
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS business_ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL UNIQUE,
    primary_description TEXT NOT NULL,
    is_frozen BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS idea_search_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id INTEGER NOT NULL,
    term TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    FOREIGN KEY (idea_id) REFERENCES business_ideas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS source_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    UNIQUE(topic_id, source_name)
);

CREATE TABLE IF NOT EXISTS canvas_elements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    element_name TEXT NOT NULL,
    content TEXT NOT NULL,
    user_feedback TEXT,
    is_frozen BOOLEAN NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    UNIQUE(topic_id, element_name)
);

CREATE TABLE IF NOT EXISTS voice_personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    communication_style TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS plan_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    section_name TEXT NOT NULL,
    content TEXT NOT NULL,
    user_feedback TEXT,
    is_frozen BOOLEAN NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    UNIQUE(topic_id, section_name)
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    step_key TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    personality_mode TEXT NOT NULL DEFAULT '',
    review_notes TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    UNIQUE(topic_id, step_key)
);

CREATE TABLE IF NOT EXISTS personality_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    personality_mode TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    UNIQUE(topic_id, agent_name)
);

CREATE TABLE IF NOT EXISTS specialist_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    section_name TEXT NOT NULL,
    specialist_id TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    UNIQUE(topic_id, section_name)
);
"""

_initialized_databases: set[str] = set()


def init_schema(conn: sqlite3.Connection) -> None:
    """Execute the schema SQL to create all tables.

    Uses executescript to handle multiple statements. Safe to call
    multiple times due to IF NOT EXISTS clauses.
    """
    conn.executescript(SCHEMA_SQL)


def get_connection(database_path: Path) -> sqlite3.Connection:
    """Create a SQLite connection and initialize the schema on first use.

    Args:
        database_path: Path to the SQLite database file. Parent directories
            are created automatically if they don't exist.

    Returns:
        A sqlite3.Connection with foreign keys enabled and schema initialized.
    """
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(database_path), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")

    db_key = str(database_path.resolve())
    if db_key not in _initialized_databases:
        init_schema(conn)

        # Add frozen column to existing tables (if upgrading from older version)
        add_frozen_columns(conn)

        _initialized_databases.add(db_key)

    return conn


def add_frozen_columns(conn: sqlite3.Connection) -> None:
    """Add is_frozen column to tables if it doesn't exist (migration for v1.1)."""
    tables_to_update = [
        ("business_ideas", "is_frozen"),
        ("canvas_elements", "is_frozen"),
        ("plan_sections", "is_frozen"),
    ]

    for table_name, column_name in tables_to_update:
        try:
            # Check if column exists
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]

            if column_name not in columns:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} BOOLEAN NOT NULL DEFAULT 0")
        except Exception:
            # Column might already exist or table might not exist
            pass
