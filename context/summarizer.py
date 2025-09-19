"""
Context Summarizer - Progressive summarization for hierarchical context management
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from context.session_database import ContextThread, SessionDatabase, SessionMetadata, SessionSummary
from memory.models import SearchResult
from memory.storage import MemoryStorage

logger = logging.getLogger(__name__)


@dataclass
class ContextHierarchy:
    """Hierarchical context structure"""

    immediate: List[SessionSummary]  # Last 2 hours
    recent: List[SessionSummary]  # Last 24 hours
    historical: List[SessionSummary]  # Last week


@dataclass
class CompressedContext:
    """Compressed context for efficient storage"""

    original_content: str
    compressed_content: str
    compression_ratio: float
    key_points: List[str]
    semantic_tags: List[str]


class ContextSummarizer:
    """Creates progressive context summaries for efficient retrieval"""

    def __init__(self, session_db: SessionDatabase, memory_storage: MemoryStorage):
        self.session_db = session_db
        self.memory_storage = memory_storage

        # Time windows for hierarchical context
        self.immediate_window = timedelta(hours=2)
        self.recent_window = timedelta(hours=24)
        self.historical_window = timedelta(days=7)

        # Compression settings
        self.target_compression_ratio = 0.3  # Compress to 30% of original

    def summarize_session(self, session: SessionMetadata) -> SessionSummary:
        """Create a comprehensive summary of a completed session"""

        if not session.end_time:
            logger.warning(f"Cannot summarize incomplete session {session.id}")
            return self._create_empty_summary(session.id)

        # Get memories associated with this session
        session_memories = self._get_session_memories(session)

        # Extract key decisions and changes
        key_decisions = self._extract_key_decisions(session_memories)
        modified_files = session.active_files.copy()

        # Generate different levels of summary
        detailed_summary = self._generate_detailed_summary(session, session_memories)
        compressed_summary = self._compress_summary(detailed_summary)

        # Determine appropriate summary level based on session age
        age = datetime.now() - session.start_time

        if age <= self.immediate_window:
            level = "immediate"
            summary_text = detailed_summary
        elif age <= self.recent_window:
            level = "recent"
            summary_text = compressed_summary.compressed_content
        else:
            level = "historical"
            summary_text = self._create_historical_summary(session, key_decisions)

        return SessionSummary(
            session_id=session.id,
            level=level,
            summary_text=summary_text,
            token_count=self._estimate_tokens(summary_text),
            created_at=datetime.now(),
            key_decisions=key_decisions,
            modified_files=modified_files,
        )

    def build_context_hierarchy(self, current_files: List[str]) -> ContextHierarchy:
        """Build hierarchical context for current files"""

        now = datetime.now()

        # Get sessions in different time windows
        immediate_sessions = self._get_sessions_in_window(now - self.immediate_window, now)
        recent_sessions = self._get_sessions_in_window(
            now - self.recent_window, now - self.immediate_window
        )
        historical_sessions = self._get_sessions_in_window(
            now - self.historical_window, now - self.recent_window
        )

        # Filter by file relevance and get/create summaries
        immediate_summaries = self._get_relevant_summaries(
            immediate_sessions, current_files, "immediate"
        )
        recent_summaries = self._get_relevant_summaries(recent_sessions, current_files, "recent")
        historical_summaries = self._get_relevant_summaries(
            historical_sessions, current_files, "historical"
        )

        return ContextHierarchy(
            immediate=immediate_summaries, recent=recent_summaries, historical=historical_summaries
        )

    def build_context_thread(self, theme: str, sessions: List[SessionMetadata]) -> ContextThread:
        """Build a context thread linking related work across sessions"""

        if not sessions:
            raise ValueError("Cannot build context thread with no sessions")

        # Extract key decisions across all sessions
        all_decisions = []
        session_ids = []

        for session in sessions:
            session_ids.append(session.id)
            memories = self._get_session_memories(session)
            decisions = self._extract_key_decisions(memories)
            all_decisions.extend(decisions)

        # Determine current status
        latest_session = max(sessions, key=lambda s: s.start_time)
        current_status = self._determine_thread_status(latest_session, all_decisions)

        return ContextThread(
            id=f"thread_{hash(theme)}_{datetime.now().isoformat()}",
            theme=theme,
            session_ids=session_ids,
            key_decisions=all_decisions,
            current_status=current_status,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def detect_semantic_duplicates(
        self, summaries: List[SessionSummary]
    ) -> List[List[SessionSummary]]:
        """Detect semantically similar summaries for deduplication"""

        duplicate_groups = []
        processed = set()

        for i, summary1 in enumerate(summaries):
            if i in processed:
                continue

            group = [summary1]
            processed.add(i)

            for j, summary2 in enumerate(summaries[i + 1 :], i + 1):
                if j in processed:
                    continue

                if self._are_semantically_similar(summary1, summary2):
                    group.append(summary2)
                    processed.add(j)

            if len(group) > 1:
                duplicate_groups.append(group)

        return duplicate_groups

    def compress_historical_context(self, summaries: List[SessionSummary]) -> CompressedContext:
        """Compress historical context to save tokens"""

        if not summaries:
            return CompressedContext("", "", 1.0, [], [])

        # Combine all summary text
        original_content = "\n".join(s.summary_text for s in summaries)

        # Extract key points and themes
        key_points = self._extract_key_points(summaries)
        semantic_tags = self._extract_semantic_tags(summaries)

        # Create compressed version
        compressed_content = self._create_compressed_narrative(key_points, semantic_tags)

        compression_ratio = len(compressed_content) / max(len(original_content), 1)

        return CompressedContext(
            original_content=original_content,
            compressed_content=compressed_content,
            compression_ratio=compression_ratio,
            key_points=key_points,
            semantic_tags=semantic_tags,
        )

    def _get_session_memories(self, session: SessionMetadata) -> List[SearchResult]:
        """Get all memories associated with a session"""
        # This would typically search memories by timestamp and files
        # For now, return empty list as this requires memory storage integration
        return []

    def _extract_key_decisions(self, memories: List[SearchResult]) -> List[str]:
        """Extract key decisions from session memories"""
        decisions = []

        for memory in memories:
            if memory.memory.type == "decision":
                decisions.append(memory.memory.content)

        return decisions

    def _generate_detailed_summary(
        self, session: SessionMetadata, memories: List[SearchResult]
    ) -> str:
        """Generate detailed summary for immediate context"""

        duration = ""
        if session.end_time and session.start_time:
            duration_minutes = int((session.end_time - session.start_time).total_seconds() / 60)
            duration = f" ({duration_minutes}min)"

        lines = [
            f"## Session {session.start_time.strftime('%H:%M')}{duration}",
            f"**Branch:** {session.branch}",
            f"**Files:** {', '.join(session.active_files[:5])}"
            + ("..." if len(session.active_files) > 5 else ""),
        ]

        if session.git_commits:
            lines.append(f"**Commits:** {len(session.git_commits)} commits")

        # Add key decisions
        key_decisions = self._extract_key_decisions(memories)
        if key_decisions:
            lines.append("**Key Decisions:**")
            for decision in key_decisions[:3]:  # Limit to top 3
                lines.append(f"- {decision}")

        # Add context summary if available
        if session.context_summary:
            lines.append(f"**Summary:** {session.context_summary}")

        return "\n".join(lines)

    def _compress_summary(self, detailed_summary: str) -> CompressedContext:
        """Compress a detailed summary"""

        # Extract key information using regex
        key_info = []

        # Extract branch
        branch_match = re.search(r"\*\*Branch:\*\* (.+)", detailed_summary)
        if branch_match:
            key_info.append(f"Branch: {branch_match.group(1)}")

        # Extract file count
        files_match = re.search(r"\*\*Files:\*\* (.+)", detailed_summary)
        if files_match:
            files_text = files_match.group(1)
            file_count = len(files_text.split(","))
            key_info.append(f"Files: {file_count}")

        # Extract decisions
        decisions = re.findall(r"- (.+)", detailed_summary)
        if decisions:
            key_info.append(f"Decisions: {len(decisions)} made")

        compressed = f"Session: {', '.join(key_info)}"
        compression_ratio = len(compressed) / max(len(detailed_summary), 1)

        return CompressedContext(
            original_content=detailed_summary,
            compressed_content=compressed,
            compression_ratio=compression_ratio,
            key_points=key_info,
            semantic_tags=[],
        )

    def _create_historical_summary(self, session: SessionMetadata, key_decisions: List[str]) -> str:
        """Create ultra-compressed historical summary"""

        date = session.start_time.strftime("%m/%d")
        file_count = len(session.active_files)

        summary_parts = [f"{date}"]

        if key_decisions:
            summary_parts.append(f"{len(key_decisions)} decisions")

        if file_count > 0:
            summary_parts.append(f"{file_count} files")

        if session.branch != "main":
            summary_parts.append(f"({session.branch})")

        return " • ".join(summary_parts)

    def _get_sessions_in_window(
        self, start_time: datetime, end_time: datetime
    ) -> List[SessionMetadata]:
        """Get sessions within a time window"""
        recent_sessions = self.session_db.get_recent_sessions(hours=168)  # Last week

        return [
            session for session in recent_sessions if start_time <= session.start_time <= end_time
        ]

    def _get_relevant_summaries(
        self, sessions: List[SessionMetadata], current_files: List[str], level: str
    ) -> List[SessionSummary]:
        """Get or create summaries for relevant sessions"""

        summaries = []
        current_files_set = set(current_files)

        for session in sessions:
            # Check file overlap for relevance
            session_files_set = set(session.active_files)
            overlap = len(current_files_set & session_files_set)

            if overlap > 0:  # Any file overlap makes it relevant
                # Try to get existing summary
                existing_summaries = self.session_db.get_session_summaries(session.id)
                level_summary = next((s for s in existing_summaries if s.level == level), None)

                if level_summary:
                    summaries.append(level_summary)
                else:
                    # Create new summary
                    new_summary = self.summarize_session(session)
                    self.session_db.store_session_summary(new_summary)
                    summaries.append(new_summary)

        return summaries

    def _are_semantically_similar(self, summary1: SessionSummary, summary2: SessionSummary) -> bool:
        """Check if two summaries are semantically similar"""

        # Simple similarity check based on file overlap and content
        files1 = set(summary1.modified_files)
        files2 = set(summary2.modified_files)

        file_overlap = len(files1 & files2) / max(len(files1 | files2), 1)

        # Check content similarity (basic)
        content_similarity = self._calculate_text_similarity(
            summary1.summary_text, summary2.summary_text
        )

        return file_overlap > 0.7 or content_similarity > 0.8

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate basic text similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _extract_key_points(self, summaries: List[SessionSummary]) -> List[str]:
        """Extract key points from multiple summaries"""
        key_points = []

        for summary in summaries:
            # Extract decisions
            key_points.extend(summary.key_decisions)

            # Extract file information
            if summary.modified_files:
                key_points.append(f"Modified {len(summary.modified_files)} files")

        # Deduplicate
        return list(set(key_points))

    def _extract_semantic_tags(self, summaries: List[SessionSummary]) -> List[str]:
        """Extract semantic tags from summaries"""
        tags = set()

        for summary in summaries:
            text = summary.summary_text.lower()

            # Technology tags
            if any(word in text for word in ["api", "endpoint", "rest"]):
                tags.add("api")
            if any(word in text for word in ["ui", "frontend", "component"]):
                tags.add("frontend")
            if any(word in text for word in ["db", "database", "model"]):
                tags.add("database")
            if any(word in text for word in ["test", "testing", "spec"]):
                tags.add("testing")
            if any(word in text for word in ["auth", "security", "login"]):
                tags.add("auth")

        return list(tags)

    def _create_compressed_narrative(self, key_points: List[str], semantic_tags: List[str]) -> str:
        """Create a compressed narrative from key points"""

        if not key_points:
            return "No significant activity"

        # Group related points
        decision_points = [
            p for p in key_points if "decision" in p.lower() or "decided" in p.lower()
        ]
        file_points = [p for p in key_points if "file" in p.lower() or "modified" in p.lower()]

        narrative_parts = []

        if decision_points:
            narrative_parts.append(f"Made {len(decision_points)} key decisions")

        if file_points:
            narrative_parts.append("worked on multiple files")

        if semantic_tags:
            narrative_parts.append(f"Areas: {', '.join(semantic_tags)}")

        return " • ".join(narrative_parts) if narrative_parts else "General development work"

    def _determine_thread_status(
        self, latest_session: SessionMetadata, decisions: List[str]
    ) -> str:
        """Determine the current status of a context thread"""

        if not latest_session.end_time:
            return "in_progress"

        # Check recency
        time_since_last = datetime.now() - latest_session.start_time
        if time_since_last > timedelta(days=7):
            return "dormant"

        # Analyze decisions for completion indicators
        decision_text = " ".join(decisions).lower()
        if any(word in decision_text for word in ["complete", "finished", "done", "shipped"]):
            return "completed"

        if any(word in decision_text for word in ["blocked", "waiting", "pending"]):
            return "blocked"

        return "active"

    def _create_empty_summary(self, session_id: str) -> SessionSummary:
        """Create empty summary for error cases"""
        return SessionSummary(
            session_id=session_id,
            level="immediate",
            summary_text="No summary available",
            token_count=0,
            created_at=datetime.now(),
            key_decisions=[],
            modified_files=[],
        )

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        return int(len(text.split()) * 1.3)
