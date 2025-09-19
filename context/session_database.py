"""
Session Database - Persistent storage for session metadata and continuity tracking
"""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SessionMetadata:
    """Metadata for a coding session"""

    id: str
    start_time: datetime
    end_time: Optional[datetime]
    branch: str
    working_dir: str
    active_files: List[str]
    git_commits: List[str]
    context_summary: Optional[str]
    continuity_score: float
    file_access_patterns: Dict[str, int]  # file -> access_count
    total_duration_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        data["end_time"] = self.end_time.isoformat() if self.end_time else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        """Create from dictionary"""
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        data["end_time"] = datetime.fromisoformat(data["end_time"]) if data["end_time"] else None
        return cls(**data)


@dataclass
class SessionSummary:
    """Summarized session for hierarchical context"""

    session_id: str
    level: str  # immediate/recent/historical
    summary_text: str
    token_count: int
    created_at: datetime
    key_decisions: List[str]
    modified_files: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSummary":
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class ContextThread:
    """Thread of related work across multiple sessions"""

    id: str
    theme: str
    session_ids: List[str]
    key_decisions: List[str]
    current_status: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextThread":
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class SessionDatabase:
    """Persistent storage for session tracking and context management"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    branch TEXT NOT NULL,
                    working_dir TEXT NOT NULL,
                    active_files TEXT NOT NULL,  -- JSON
                    git_commits TEXT NOT NULL,   -- JSON
                    context_summary TEXT,
                    continuity_score REAL NOT NULL,
                    file_access_patterns TEXT NOT NULL,  -- JSON
                    total_duration_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Session summaries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    level TEXT NOT NULL,  -- immediate/recent/historical
                    summary_text TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    key_decisions TEXT NOT NULL,  -- JSON
                    modified_files TEXT NOT NULL,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)

            # Context threads table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_threads (
                    id TEXT PRIMARY KEY,
                    theme TEXT NOT NULL,
                    session_ids TEXT NOT NULL,  -- JSON
                    key_decisions TEXT NOT NULL,  -- JSON
                    current_status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_branch ON sessions(branch)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_working_dir ON sessions(working_dir)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_summaries_session_id ON session_summaries(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_summaries_level ON session_summaries(level)"
            )

    def store_session(self, session: SessionMetadata) -> str:
        """Store a session in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    id, start_time, end_time, branch, working_dir,
                    active_files, git_commits, context_summary,
                    continuity_score, file_access_patterns, total_duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session.id,
                    session.start_time.isoformat(),
                    session.end_time.isoformat() if session.end_time else None,
                    session.branch,
                    session.working_dir,
                    json.dumps(session.active_files),
                    json.dumps(session.git_commits),
                    session.context_summary,
                    session.continuity_score,
                    json.dumps(session.file_access_patterns),
                    session.total_duration_seconds,
                ),
            )
        return session.id

    def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Get a session by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return SessionMetadata(
                id=row["id"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                branch=row["branch"],
                working_dir=row["working_dir"],
                active_files=json.loads(row["active_files"]),
                git_commits=json.loads(row["git_commits"]),
                context_summary=row["context_summary"],
                continuity_score=row["continuity_score"],
                file_access_patterns=json.loads(row["file_access_patterns"]),
                total_duration_seconds=row["total_duration_seconds"],
            )

    def get_recent_sessions(self, hours: int = 24, limit: int = 10) -> List[SessionMetadata]:
        """Get recent sessions within the specified time window"""
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                WHERE start_time >= ?
                ORDER BY start_time DESC
                LIMIT ?
            """,
                (cutoff.isoformat(), limit),
            )

            sessions = []
            for row in cursor.fetchall():
                sessions.append(
                    SessionMetadata(
                        id=row["id"],
                        start_time=datetime.fromisoformat(row["start_time"]),
                        end_time=datetime.fromisoformat(row["end_time"])
                        if row["end_time"]
                        else None,
                        branch=row["branch"],
                        working_dir=row["working_dir"],
                        active_files=json.loads(row["active_files"]),
                        git_commits=json.loads(row["git_commits"]),
                        context_summary=row["context_summary"],
                        continuity_score=row["continuity_score"],
                        file_access_patterns=json.loads(row["file_access_patterns"]),
                        total_duration_seconds=row["total_duration_seconds"],
                    )
                )

            return sessions

    def get_last_session(self, working_dir: Optional[str] = None) -> Optional[SessionMetadata]:
        """Get the most recent session, optionally filtered by working directory"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if working_dir:
                cursor = conn.execute(
                    """
                    SELECT * FROM sessions
                    WHERE working_dir = ?
                    ORDER BY start_time DESC
                    LIMIT 1
                """,
                    (working_dir,),
                )
            else:
                cursor = conn.execute("""
                    SELECT * FROM sessions
                    ORDER BY start_time DESC
                    LIMIT 1
                """)

            row = cursor.fetchone()
            if not row:
                return None

            return SessionMetadata(
                id=row["id"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                branch=row["branch"],
                working_dir=row["working_dir"],
                active_files=json.loads(row["active_files"]),
                git_commits=json.loads(row["git_commits"]),
                context_summary=row["context_summary"],
                continuity_score=row["continuity_score"],
                file_access_patterns=json.loads(row["file_access_patterns"]),
                total_duration_seconds=row["total_duration_seconds"],
            )

    def end_session(self, session_id: str, context_summary: Optional[str] = None) -> bool:
        """Mark a session as ended"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE sessions
                SET end_time = ?, context_summary = ?
                WHERE id = ? AND end_time IS NULL
            """,
                (datetime.now().isoformat(), context_summary, session_id),
            )

            return cursor.rowcount > 0

    def store_session_summary(self, summary: SessionSummary) -> int:
        """Store a session summary"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO session_summaries (
                    session_id, level, summary_text, token_count,
                    key_decisions, modified_files
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    summary.session_id,
                    summary.level,
                    summary.summary_text,
                    summary.token_count,
                    json.dumps(summary.key_decisions),
                    json.dumps(summary.modified_files),
                ),
            )
            return cursor.lastrowid

    def get_session_summaries(self, session_id: str) -> List[SessionSummary]:
        """Get all summaries for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM session_summaries
                WHERE session_id = ?
                ORDER BY created_at DESC
            """,
                (session_id,),
            )

            summaries = []
            for row in cursor.fetchall():
                summaries.append(
                    SessionSummary(
                        session_id=row["session_id"],
                        level=row["level"],
                        summary_text=row["summary_text"],
                        token_count=row["token_count"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        key_decisions=json.loads(row["key_decisions"]),
                        modified_files=json.loads(row["modified_files"]),
                    )
                )

            return summaries

    def store_context_thread(self, thread: ContextThread) -> str:
        """Store a context thread"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO context_threads (
                    id, theme, session_ids, key_decisions, current_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    thread.id,
                    thread.theme,
                    json.dumps(thread.session_ids),
                    json.dumps(thread.key_decisions),
                    thread.current_status,
                    thread.created_at.isoformat(),
                    thread.updated_at.isoformat(),
                ),
            )
        return thread.id

    def get_active_context_threads(self, limit: int = 5) -> List[ContextThread]:
        """Get active context threads"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM context_threads
                WHERE current_status != 'completed'
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                (limit,),
            )

            threads = []
            for row in cursor.fetchall():
                threads.append(
                    ContextThread(
                        id=row["id"],
                        theme=row["theme"],
                        session_ids=json.loads(row["session_ids"]),
                        key_decisions=json.loads(row["key_decisions"]),
                        current_status=row["current_status"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                    )
                )

            return threads

    def get_file_activity_history(self, file_path: str, days: int = 7) -> List[SessionMetadata]:
        """Get sessions where a specific file was active"""
        cutoff = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                WHERE start_time >= ? AND active_files LIKE ?
                ORDER BY start_time DESC
            """,
                (cutoff.isoformat(), f"%{file_path}%"),
            )

            sessions = []
            for row in cursor.fetchall():
                active_files = json.loads(row["active_files"])
                if file_path in active_files:
                    sessions.append(
                        SessionMetadata(
                            id=row["id"],
                            start_time=datetime.fromisoformat(row["start_time"]),
                            end_time=datetime.fromisoformat(row["end_time"])
                            if row["end_time"]
                            else None,
                            branch=row["branch"],
                            working_dir=row["working_dir"],
                            active_files=active_files,
                            git_commits=json.loads(row["git_commits"]),
                            context_summary=row["context_summary"],
                            continuity_score=row["continuity_score"],
                            file_access_patterns=json.loads(row["file_access_patterns"]),
                            total_duration_seconds=row["total_duration_seconds"],
                        )
                    )

            return sessions

    def cleanup_old_sessions(self, days: int = 30):
        """Remove sessions older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            # First, clean up summaries for old sessions
            conn.execute(
                """
                DELETE FROM session_summaries
                WHERE session_id IN (
                    SELECT id FROM sessions WHERE start_time < ?
                )
            """,
                (cutoff.isoformat(),),
            )

            # Then clean up the sessions themselves
            cursor = conn.execute(
                """
                DELETE FROM sessions WHERE start_time < ?
            """,
                (cutoff.isoformat(),),
            )

            return cursor.rowcount
