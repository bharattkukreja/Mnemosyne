"""
Session Tracker - Intelligent detection of session boundaries and continuity
"""

import logging
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from context.session_database import SessionDatabase, SessionMetadata

logger = logging.getLogger(__name__)


class SessionBoundaryType(Enum):
    """Types of session boundaries"""

    NEW_SESSION = "new_session"
    CONTINUATION = "continuation"
    BRANCH_SWITCH = "branch_switch"
    DIRECTORY_CHANGE = "directory_change"
    LONG_GAP = "long_gap"


@dataclass
class SessionBoundary:
    """Information about a detected session boundary"""

    boundary_type: SessionBoundaryType
    confidence: float
    reasons: List[str]
    previous_session_id: Optional[str]
    should_inject_context: bool


@dataclass
class FileActivity:
    """File activity tracking"""

    file_path: str
    access_count: int
    last_accessed: datetime
    modification_detected: bool


class SessionTracker:
    """Tracks session boundaries and maintains session continuity"""

    def __init__(self, config: Dict, session_db: SessionDatabase):
        self.config = config
        self.session_db = session_db
        self.current_session: Optional[SessionMetadata] = None

        # Configuration
        self.boundary_time_threshold = config.get("boundary_time_threshold", 1800)  # 30 minutes
        self.file_continuity_threshold = config.get("file_continuity_threshold", 0.7)
        self.max_session_duration = config.get("max_session_duration", 14400)  # 4 hours

        # Session state
        self.file_activities: Dict[str, FileActivity] = {}
        self.session_start_time = datetime.now()

    def detect_session_boundary(
        self, current_files: List[str], working_dir: str, git_branch: str
    ) -> SessionBoundary:
        """Detect if this represents a new session or continuation"""

        # Get the last session
        last_session = self.session_db.get_last_session(working_dir)

        if not last_session:
            return SessionBoundary(
                boundary_type=SessionBoundaryType.NEW_SESSION,
                confidence=1.0,
                reasons=["No previous session found"],
                previous_session_id=None,
                should_inject_context=False,
            )

        # Calculate various signals
        time_gap = self._calculate_time_gap(last_session)
        file_continuity = self._calculate_file_continuity(current_files, last_session.active_files)
        branch_changed = git_branch != last_session.branch
        directory_changed = working_dir != last_session.working_dir

        reasons = []
        confidence = 0.0

        # Time-based boundary detection
        if time_gap > timedelta(seconds=self.max_session_duration):
            return SessionBoundary(
                boundary_type=SessionBoundaryType.LONG_GAP,
                confidence=0.9,
                reasons=[f"Long time gap: {time_gap}"],
                previous_session_id=last_session.id,
                should_inject_context=True,
            )

        # Branch change boundary
        if branch_changed:
            return SessionBoundary(
                boundary_type=SessionBoundaryType.BRANCH_SWITCH,
                confidence=0.8,
                reasons=[f"Branch changed: {last_session.branch} → {git_branch}"],
                previous_session_id=last_session.id,
                should_inject_context=True,
            )

        # Directory change boundary
        if directory_changed:
            return SessionBoundary(
                boundary_type=SessionBoundaryType.DIRECTORY_CHANGE,
                confidence=0.7,
                reasons=[f"Directory changed: {last_session.working_dir} → {working_dir}"],
                previous_session_id=last_session.id,
                should_inject_context=True,
            )

        # Time gap analysis
        if time_gap > timedelta(seconds=self.boundary_time_threshold):
            confidence += 0.5
            reasons.append(f"Time gap: {time_gap}")

        # File continuity analysis
        if file_continuity < self.file_continuity_threshold:
            confidence += 0.3
            reasons.append(f"Low file continuity: {file_continuity:.2f}")
        else:
            confidence -= 0.2
            reasons.append(f"High file continuity: {file_continuity:.2f}")

        # Determine boundary type
        if confidence >= 0.6:
            return SessionBoundary(
                boundary_type=SessionBoundaryType.NEW_SESSION,
                confidence=confidence,
                reasons=reasons,
                previous_session_id=last_session.id,
                should_inject_context=True,
            )
        else:
            return SessionBoundary(
                boundary_type=SessionBoundaryType.CONTINUATION,
                confidence=1.0 - confidence,
                reasons=reasons,
                previous_session_id=last_session.id,
                should_inject_context=False,
            )

    def start_new_session(
        self,
        current_files: List[str],
        working_dir: str,
        git_branch: str,
        git_commits: Optional[List[str]] = None,
    ) -> str:
        """Start tracking a new session"""

        # End previous session if exists
        if self.current_session and not self.current_session.end_time:
            self.end_current_session()

        # Create new session
        session_id = str(uuid.uuid4())
        self.current_session = SessionMetadata(
            id=session_id,
            start_time=datetime.now(),
            end_time=None,
            branch=git_branch,
            working_dir=working_dir,
            active_files=current_files.copy(),
            git_commits=git_commits or [],
            context_summary=None,
            continuity_score=0.0,
            file_access_patterns={},
        )

        # Initialize file activities
        for file_path in current_files:
            self.track_file_activity(file_path)

        # Store in database
        self.session_db.store_session(self.current_session)

        logger.info(f"Started new session {session_id} with {len(current_files)} files")
        return session_id

    def update_current_session(self, current_files: List[str]):
        """Update the current session with new file activity"""
        if not self.current_session:
            return

        # Update active files
        self.current_session.active_files = current_files.copy()

        # Track file activities
        for file_path in current_files:
            self.track_file_activity(file_path)

        # Update file access patterns
        self.current_session.file_access_patterns = {
            fp: activity.access_count for fp, activity in self.file_activities.items()
        }

        # Calculate continuity score
        self.current_session.continuity_score = self._calculate_session_continuity()

        # Save to database
        self.session_db.store_session(self.current_session)

    def end_current_session(self, context_summary: Optional[str] = None):
        """End the current session"""
        if not self.current_session:
            return

        # Calculate total duration
        if self.current_session.start_time:
            duration = datetime.now() - self.current_session.start_time
            self.current_session.total_duration_seconds = int(duration.total_seconds())

        # Update end time and summary
        self.current_session.end_time = datetime.now()
        self.current_session.context_summary = context_summary

        # Final save
        self.session_db.store_session(self.current_session)

        logger.info(f"Ended session {self.current_session.id}, duration: {duration}")
        self.current_session = None

    def track_file_activity(self, file_path: str):
        """Track activity on a specific file"""
        if file_path not in self.file_activities:
            self.file_activities[file_path] = FileActivity(
                file_path=file_path,
                access_count=0,
                last_accessed=datetime.now(),
                modification_detected=False,
            )

        activity = self.file_activities[file_path]
        activity.access_count += 1
        activity.last_accessed = datetime.now()

        # Detect if file was modified (basic check)
        try:
            file_stat = Path(file_path).stat()
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            if file_mtime > activity.last_accessed - timedelta(minutes=5):
                activity.modification_detected = True
        except:
            pass

    def get_session_continuity_score(self, session_id: str) -> float:
        """Calculate continuity score for a session"""
        session = self.session_db.get_session(session_id)
        if not session:
            return 0.0

        score = 0.0

        # File consistency factor
        if session.active_files:
            # More files = more context = higher continuity potential
            file_factor = min(len(session.active_files) / 10.0, 1.0)
            score += file_factor * 0.3

        # Time factor
        if session.total_duration_seconds:
            # Optimal session length is 1-2 hours
            duration_hours = session.total_duration_seconds / 3600
            if 0.5 <= duration_hours <= 3.0:
                time_factor = 1.0 - abs(duration_hours - 1.5) / 1.5
                score += time_factor * 0.4
            else:
                score += 0.1

        # Activity pattern factor
        if session.file_access_patterns:
            # Even distribution of access is better for continuity
            access_counts = list(session.file_access_patterns.values())
            if access_counts:
                avg_access = sum(access_counts) / len(access_counts)
                variance = sum((x - avg_access) ** 2 for x in access_counts) / len(access_counts)
                activity_factor = 1.0 / (1.0 + variance / max(avg_access, 1))
                score += activity_factor * 0.3

        return min(score, 1.0)

    def get_file_history_sessions(self, file_path: str, days: int = 7) -> List[SessionMetadata]:
        """Get sessions where a file was active"""
        return self.session_db.get_file_activity_history(file_path, days)

    def should_inject_context(self, boundary: SessionBoundary) -> bool:
        """Determine if context should be injected based on session boundary"""
        return boundary.should_inject_context

    def _calculate_time_gap(self, last_session: SessionMetadata) -> timedelta:
        """Calculate time gap between sessions"""
        if last_session.end_time:
            return datetime.now() - last_session.end_time
        else:
            # Session never ended, use start time + estimated duration
            estimated_end = last_session.start_time + timedelta(hours=2)
            return datetime.now() - estimated_end

    def _calculate_file_continuity(
        self, current_files: List[str], previous_files: List[str]
    ) -> float:
        """Calculate file continuity between sessions"""
        if not previous_files:
            return 0.0

        current_set = set(current_files)
        previous_set = set(previous_files)

        if not current_set:
            return 0.0

        overlap = current_set & previous_set
        union = current_set | previous_set

        return len(overlap) / len(union) if union else 0.0

    def _calculate_session_continuity(self) -> float:
        """Calculate continuity score for the current session"""
        if not self.current_session:
            return 0.0

        # Get previous session for comparison
        previous_session = None
        recent_sessions = self.session_db.get_recent_sessions(hours=48, limit=5)
        for session in recent_sessions:
            if session.id != self.current_session.id:
                previous_session = session
                break

        if not previous_session:
            return 0.5  # Default for first session

        # Calculate file continuity
        file_continuity = self._calculate_file_continuity(
            self.current_session.active_files, previous_session.active_files
        )

        # Calculate time continuity
        time_gap = self._calculate_time_gap(previous_session)
        time_continuity = max(0.0, 1.0 - time_gap.total_seconds() / (4 * 3600))  # 4 hour decay

        # Branch continuity
        branch_continuity = 1.0 if self.current_session.branch == previous_session.branch else 0.3

        # Weighted average
        continuity = file_continuity * 0.5 + time_continuity * 0.3 + branch_continuity * 0.2

        return min(continuity, 1.0)

    def _get_current_git_branch(self) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"], capture_output=True, text=True, cwd=Path.cwd()
            )
            return result.stdout.strip() if result.returncode == 0 else "main"
        except:
            return "main"

    def _get_recent_commits(self, count: int = 5) -> List[str]:
        """Get recent git commits"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", f"-{count}"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
        except:
            pass
        return []

    def get_session_stats(self) -> Dict:
        """Get statistics about sessions"""
        recent_sessions = self.session_db.get_recent_sessions(hours=168)  # Last week

        if not recent_sessions:
            return {"total_sessions": 0, "avg_duration": 0, "avg_continuity": 0}

        total_duration = sum(s.total_duration_seconds or 0 for s in recent_sessions)
        avg_duration = total_duration / len(recent_sessions) / 3600  # Convert to hours

        avg_continuity = sum(s.continuity_score for s in recent_sessions) / len(recent_sessions)

        return {
            "total_sessions": len(recent_sessions),
            "avg_duration_hours": avg_duration,
            "avg_continuity": avg_continuity,
            "active_files_count": len(set().union(*(s.active_files for s in recent_sessions))),
            "branches_used": len(set(s.branch for s in recent_sessions)),
        }
