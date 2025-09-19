"""
Smart Context Injection - The Killer Feature
Automatically injects relevant context at session start to save developers
from manually re-establishing context, reducing overall token usage.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from context.compressor import ContextCompressor
from context.relevance import RelevanceScorer
from context.session_database import SessionDatabase
from context.session_tracker import SessionTracker
from context.summarizer import ContextSummarizer
from memory.models import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Context for the current coding session"""

    current_files: List[str]
    recent_commits: List[str]
    active_branch: str
    project_root: str
    session_start_time: datetime
    working_directory: str
    recent_file_changes: List[str]


@dataclass
class InjectionResult:
    """Result of context injection"""

    injected_context: str
    token_count: int
    memories_included: int
    context_efficiency_score: float  # How much context per token
    auto_trigger_confidence: float  # How confident we are this is useful


class SmartContextInjector:
    """Automatically inject the most relevant context to save developer token usage"""

    def __init__(
        self, config: Dict[str, Any], session_db_path: Optional[str] = None, memory_storage=None
    ):
        self.config = config
        self.relevance_scorer = RelevanceScorer()
        self.compressor = ContextCompressor()

        # Initialize session tracking
        if session_db_path:
            self.session_db = SessionDatabase(session_db_path)
            self.session_tracker = SessionTracker(config, self.session_db)
            # Initialize summarizer
            if memory_storage:
                self.summarizer = ContextSummarizer(self.session_db, memory_storage)
            else:
                self.summarizer = None
        else:
            self.session_db = None
            self.session_tracker = None
            self.summarizer = None

        # Efficiency-focused settings
        self.max_auto_inject_tokens = config.get("auto_inject_max_tokens", 800)  # Conservative
        self.confidence_threshold = config.get("auto_inject_confidence", 0.7)
        self.min_context_efficiency = config.get("min_context_efficiency", 0.5)

    async def detect_session_start(self, current_session: SessionContext) -> bool:
        """Detect if this is a new session that needs context injection"""

        if not self.session_tracker:
            # Fallback to simple time-based detection
            return True

        # Use session tracker for sophisticated boundary detection
        boundary = self.session_tracker.detect_session_boundary(
            current_files=current_session.current_files,
            working_dir=current_session.working_directory,
            git_branch=current_session.active_branch,
        )

        # Start tracking the current session
        if boundary.should_inject_context:
            session_id = self.session_tracker.start_new_session(
                current_files=current_session.current_files,
                working_dir=current_session.working_directory,
                git_branch=current_session.active_branch,
                git_commits=current_session.recent_commits,
            )
            logger.info(
                f"New session detected: {boundary.boundary_type.value}, session_id: {session_id}"
            )
        else:
            # Update existing session
            self.session_tracker.update_current_session(current_session.current_files)

        return boundary.should_inject_context

    async def generate_auto_injection(
        self, session: SessionContext, all_memories: List[SearchResult], force: bool = False
    ) -> Optional[InjectionResult]:
        """Generate optimal context injection for session start"""

        # Step 1: Get highly relevant memories
        relevant_memories = await self._get_session_relevant_memories(session, all_memories)

        if not relevant_memories:
            # For forced injection, use any available memories
            if force and all_memories:
                # Take the most recent memories if no relevant ones found
                relevant_memories = sorted(
                    all_memories, key=lambda x: x.memory.timestamp, reverse=True
                )[:5]
            else:
                return None

        # Step 2: Optimize for maximum context per token
        optimized_context = await self._optimize_context_density(relevant_memories, session)

        # Step 3: Calculate efficiency metrics
        efficiency_score = self._calculate_context_efficiency(optimized_context, relevant_memories)

        # For forced injection, bypass efficiency check
        if not force and efficiency_score < self.min_context_efficiency:
            return None

        # Step 4: Build injection
        injection = await self._build_efficient_injection(optimized_context, session)

        return InjectionResult(
            injected_context=injection["content"],
            token_count=injection["tokens"],
            memories_included=len(optimized_context),
            context_efficiency_score=efficiency_score,
            auto_trigger_confidence=injection["confidence"],
        )

    async def _get_session_relevant_memories(
        self, session: SessionContext, all_memories: List[SearchResult]
    ) -> List[SearchResult]:
        """Get memories most relevant to current session using hierarchical context"""

        # If we have a summarizer, use hierarchical context
        if self.summarizer:
            return await self._get_hierarchical_context(session, all_memories)

        # Fallback to original implementation
        query_context = {
            "current_files": session.current_files,
            "recent_commits": session.recent_commits,
            "active_branch": session.active_branch,
            "recent_changes": session.recent_file_changes,
            "intent": "session_context",
            "tags": self.relevance_scorer._extract_tags_from_files(session.current_files),
            "session_indicators": await self._get_session_indicators(session),
        }

        # Score memories with session context
        scored_memories = self.relevance_scorer.score_memories(all_memories, query_context)

        # Filter for high relevance only (save tokens)
        high_relevance = [m for m in scored_memories if m.relevance_score > 0.4]

        return high_relevance[:15]  # Limit candidates

    async def _get_hierarchical_context(
        self, session: SessionContext, all_memories: List[SearchResult]
    ) -> List[SearchResult]:
        """Get context using hierarchical summarization"""

        # Build context hierarchy based on current files
        context_hierarchy = self.summarizer.build_context_hierarchy(session.current_files)

        # Convert session summaries to pseudo-memories for processing
        pseudo_memories = []

        # Process immediate context (highest priority, full detail)
        for summary in context_hierarchy.immediate:
            pseudo_memory = self._create_pseudo_memory_from_summary(summary, priority=1.0)
            pseudo_memories.append(pseudo_memory)

        # Process recent context (medium priority, some compression)
        for summary in context_hierarchy.recent:
            pseudo_memory = self._create_pseudo_memory_from_summary(summary, priority=0.7)
            pseudo_memories.append(pseudo_memory)

        # Process historical context (low priority, highly compressed)
        if len(pseudo_memories) < 10:  # Only include if we have token budget
            for summary in context_hierarchy.historical[:3]:  # Limit historical items
                pseudo_memory = self._create_pseudo_memory_from_summary(summary, priority=0.4)
                pseudo_memories.append(pseudo_memory)

        # Combine with actual memories from the current session timeframe
        recent_memories = [
            m
            for m in all_memories
            if (datetime.now() - m.memory.timestamp).total_seconds() < 7200  # Last 2 hours
        ]

        # Merge and prioritize
        all_context = pseudo_memories + recent_memories
        return sorted(all_context, key=lambda x: x.relevance_score, reverse=True)[:15]

    def _create_pseudo_memory_from_summary(self, summary, priority: float):
        """Create a pseudo SearchResult from a session summary"""
        from memory.models import Memory, SearchResult

        # Create a pseudo-memory that looks like a regular memory
        pseudo_memory = Memory(
            id=f"summary_{summary.session_id}",
            type="session_summary",
            content=summary.summary_text,
            reasoning=f"Session summary from {summary.created_at.strftime('%H:%M')}",
            files=summary.modified_files,
            tags=[summary.level],
            timestamp=summary.created_at,
        )

        # Create search result with priority-based relevance
        return SearchResult(
            memory=pseudo_memory, similarity_score=priority, relevance_score=priority
        )

    async def _optimize_context_density(
        self, memories: List[SearchResult], session: SessionContext
    ) -> List[SearchResult]:
        """Optimize for maximum useful context per token"""

        # Calculate context density score for each memory
        density_scores = []

        for memory in memories:
            content_value = self._calculate_content_value(memory, session)
            token_cost = self._estimate_memory_tokens(memory)

            density = content_value / max(token_cost, 1)
            density_scores.append((memory, density))

        # Sort by density and select best
        density_scores.sort(key=lambda x: x[1], reverse=True)

        # Greedy selection within token budget
        selected = []
        total_tokens = 0

        for memory, density in density_scores:
            memory_tokens = self._estimate_memory_tokens(memory)

            if total_tokens + memory_tokens <= self.max_auto_inject_tokens:
                selected.append(memory)
                total_tokens += memory_tokens
            else:
                break

        return selected

    def _calculate_content_value(self, memory: SearchResult, session: SessionContext) -> float:
        """Calculate the value of this memory's content for the session"""

        value = memory.relevance_score

        # Enhanced content type importance based on context preservation needs
        content_boosts = {
            "decision": 3.0,  # Extremely high value - prevents re-discussion
            "rejected_approach": 2.5,  # Very high value - prevents re-doing work
            "session_summary": 2.2,  # High value - condensed context
            "architecture": 1.8,  # High value - structural understanding
            "bug_fix": 1.5,  # Medium-high value - prevents repeated bugs
            "context_thread": 1.3,  # Medium value - thematic continuity
            "todo": 0.9,  # Slightly lower value for auto-injection
        }

        value *= content_boosts.get(memory.memory.type, 1.0)

        # Enhanced file overlap scoring
        memory_files = set(memory.memory.files)
        current_files = set(session.current_files)
        file_overlap = len(memory_files & current_files)
        file_union = len(memory_files | current_files)

        # File relevance scoring
        if file_overlap > 0:
            overlap_ratio = file_overlap / len(current_files) if current_files else 0
            value += overlap_ratio * 1.0  # Strong boost for file relevance

        # Session continuity boost (if we have session tracking)
        if self.session_tracker and hasattr(memory.memory, "session_id"):
            # Boost memories from recent sessions with high continuity scores
            try:
                session_continuity = self.session_tracker.get_session_continuity_score(
                    memory.memory.session_id
                )
                value += session_continuity * 0.5
            except:
                pass

        # Enhanced temporal scoring
        age_hours = (datetime.now() - memory.memory.timestamp).total_seconds() / 3600

        if age_hours < 2:  # Last 2 hours - immediate context
            value += 1.0
        elif age_hours < 8:  # Last 8 hours - very recent
            value += 0.7
        elif age_hours < 24:  # Last day - recent
            value += 0.4
        elif age_hours < 168:  # Last week - somewhat recent
            value += 0.1

        # Branch continuity boost
        if hasattr(memory.memory, "branch") and memory.memory.branch == session.active_branch:
            value += 0.3

        return value

    def _estimate_memory_tokens(self, memory: SearchResult) -> int:
        """Estimate tokens for compressed memory format"""

        # Use compressed format for estimation
        compressed = self._get_compressed_format(memory)
        return len(compressed.split()) * 1.3  # Rough token estimate

    def _get_compressed_format(self, memory: SearchResult) -> str:
        """Ultra-compressed format for auto-injection with enhanced efficiency"""

        memory_type = memory.memory.type
        content = memory.memory.content
        reasoning = memory.memory.reasoning

        # Type-specific compression strategies
        if memory_type == "decision":
            return self._compress_decision(content, reasoning, memory.memory.files)
        elif memory_type == "rejected_approach":
            return self._compress_rejection(content, reasoning)
        elif memory_type == "session_summary":
            return self._compress_session_summary(content, memory.memory.files)
        elif memory_type == "bug_fix":
            return self._compress_bug_fix(content, memory.memory.files)
        else:
            return self._compress_generic(content, reasoning, memory.memory.files)

    def _compress_decision(self, content: str, reasoning: str, files: List[str]) -> str:
        """Compress decision memories with maximum information density"""

        # Extract key decision verbs and outcomes
        decision_indicators = ["decided", "chose", "selected", "will use", "going with"]
        rejection_indicators = ["rejected", "avoiding", "not using", "against"]

        compressed_parts = []

        # Try to extract the core decision
        content_lower = content.lower()
        for indicator in decision_indicators:
            if indicator in content_lower:
                # Extract the decision part
                decision_start = content_lower.find(indicator)
                decision_part = content[decision_start : decision_start + 40].strip()
                compressed_parts.append(f"✅ {decision_part}...")
                break
        else:
            # Fallback to truncated content
            compressed_parts.append(f"✅ {content[:30]}...")

        # Add rejection if present
        if reasoning:
            reasoning_lower = reasoning.lower()
            for indicator in rejection_indicators:
                if indicator in reasoning_lower:
                    reject_start = reasoning_lower.find(indicator)
                    reject_part = reasoning[reject_start : reject_start + 25].strip()
                    compressed_parts.append(f"(vs {reject_part}...)")
                    break

        # Add file context (just filename)
        if files:
            filename = files[0].split("/")[-1] if "/" in files[0] else files[0]
            compressed_parts.append(f"[{filename}]")

        return " ".join(compressed_parts)

    def _compress_rejection(self, content: str, reasoning: str) -> str:
        """Compress rejected approach memories"""

        # Extract what was rejected and why
        rejected_item = content[:25] + "..." if len(content) > 25 else content

        if reasoning:
            reason = reasoning[:20] + "..." if len(reasoning) > 20 else reasoning
            return f"❌ {rejected_item} ({reason})"
        else:
            return f"❌ {rejected_item}"

    def _compress_session_summary(self, content: str, files: List[str]) -> str:
        """Compress session summary memories"""

        # Session summaries are already compressed, just add metadata
        summary = content[:50] + "..." if len(content) > 50 else content

        if files:
            file_count = len(files)
            if file_count == 1:
                filename = files[0].split("/")[-1] if "/" in files[0] else files[0]
                return f"📝 {summary} [{filename}]"
            else:
                return f"📝 {summary} [{file_count} files]"

        return f"📝 {summary}"

    def _compress_bug_fix(self, content: str, files: List[str]) -> str:
        """Compress bug fix memories"""

        # Extract the issue and solution
        fix_content = content[:35] + "..." if len(content) > 35 else content

        if files:
            filename = files[0].split("/")[-1] if "/" in files[0] else files[0]
            return f"🐛 {fix_content} [{filename}]"

        return f"🐛 {fix_content}"

    def _compress_generic(self, content: str, reasoning: str, files: List[str]) -> str:
        """Generic compression for other memory types"""

        # Basic compression with essential info
        compressed_content = content[:40] + "..." if len(content) > 40 else content

        parts = [compressed_content]

        if reasoning and len(reasoning) > 0:
            compressed_reasoning = reasoning[:25] + "..." if len(reasoning) > 25 else reasoning
            parts.append(f"({compressed_reasoning})")

        if files:
            filename = files[0].split("/")[-1] if "/" in files[0] else files[0]
            parts.append(f"[{filename}]")

        return " ".join(parts)

    async def _build_efficient_injection(
        self, memories: List[SearchResult], session: SessionContext
    ) -> Dict[str, Any]:
        """Build the most token-efficient injection with enhanced formatting"""

        if not memories:
            return {"content": "", "tokens": 0, "confidence": 0.0}

        # Hierarchical organization for better readability
        immediate_memories = [m for m in memories if self._is_immediate_context(m)]
        recent_memories = [m for m in memories if not self._is_immediate_context(m)]

        lines = []

        # Build context with hierarchical structure
        if immediate_memories:
            lines.append("# Current Context:")
            lines.extend(self._format_memory_group(immediate_memories, max_items=5))

        if recent_memories and len(lines) < 15:  # Only add if we have token budget
            if lines:  # Add separator if we already have content
                lines.append("")
            lines.append("# Recent:")
            lines.extend(self._format_memory_group(recent_memories, max_items=3))

        # Add session-specific context hints
        context_hints = self._generate_context_hints(memories, session)
        if context_hints and len(lines) < 20:
            lines.append("")
            lines.extend(context_hints)

        content = "\n".join(lines)

        # Enhanced confidence calculation
        confidence = self._calculate_injection_confidence(memories, session)

        return {
            "content": content,
            "tokens": self._estimate_tokens(content),
            "confidence": confidence,
        }

    def _is_immediate_context(self, memory: SearchResult) -> bool:
        """Determine if memory represents immediate context"""
        age_hours = (datetime.now() - memory.memory.timestamp).total_seconds() / 3600
        return (
            age_hours < 2  # Very recent
            or memory.memory.type in ["decision", "rejected_approach"]  # High value
            or memory.relevance_score > 0.8  # Highly relevant
        )

    def _format_memory_group(self, memories: List[SearchResult], max_items: int) -> List[str]:
        """Format a group of memories efficiently"""

        # Group by type for better organization
        by_type = {}
        for memory in memories:
            mem_type = memory.memory.type
            if mem_type not in by_type:
                by_type[mem_type] = []
            by_type[mem_type].append(memory)

        lines = []
        items_added = 0

        # Priority order for memory types
        type_priority = [
            "decision",
            "rejected_approach",
            "session_summary",
            "architecture",
            "bug_fix",
            "todo",
        ]

        for mem_type in type_priority:
            if items_added >= max_items:
                break

            if mem_type in by_type:
                type_memories = by_type[mem_type]

                # Format memories of this type
                for memory in type_memories[: max_items - items_added]:
                    compressed = self._get_compressed_format(memory)
                    lines.append(f"• {compressed}")
                    items_added += 1

                # Remove processed type
                del by_type[mem_type]

        # Handle any remaining types
        for mem_type, type_memories in by_type.items():
            if items_added >= max_items:
                break

            for memory in type_memories[: max_items - items_added]:
                compressed = self._get_compressed_format(memory)
                lines.append(f"• {compressed}")
                items_added += 1

        return lines

    def _generate_context_hints(
        self, memories: List[SearchResult], session: SessionContext
    ) -> List[str]:
        """Generate helpful context hints"""

        hints = []

        # File context hints
        memory_files = set()
        for memory in memories:
            memory_files.update(memory.memory.files)

        current_files_set = set(session.current_files)
        overlapping_files = memory_files & current_files_set

        if overlapping_files:
            file_count = len(overlapping_files)
            if file_count <= 2:
                file_list = ", ".join(f.split("/")[-1] for f in list(overlapping_files)[:2])
                hints.append(f"💡 Context relates to: {file_list}")
            else:
                hints.append(f"💡 Context covers {file_count} of your current files")

        # Decision pattern hints
        decisions = [m for m in memories if m.memory.type == "decision"]
        rejections = [m for m in memories if m.memory.type == "rejected_approach"]

        if decisions and rejections:
            hints.append(
                f"⚡ {len(decisions)} decisions made, {len(rejections)} approaches avoided"
            )

        return hints

    def _calculate_injection_confidence(
        self, memories: List[SearchResult], session: SessionContext
    ) -> float:
        """Calculate confidence in the injection quality"""

        if not memories:
            return 0.0

        factors = []

        # Relevance factor
        avg_relevance = sum(m.relevance_score for m in memories) / len(memories)
        factors.append(("relevance", avg_relevance, 0.4))

        # File coverage factor
        memory_files = set()
        for memory in memories:
            memory_files.update(memory.memory.files)

        file_coverage = len(memory_files & set(session.current_files)) / max(
            len(session.current_files), 1
        )
        factors.append(("file_coverage", file_coverage, 0.3))

        # Recency factor
        recent_count = sum(1 for m in memories if self._is_immediate_context(m))
        recency_score = recent_count / max(len(memories), 1)
        factors.append(("recency", recency_score, 0.2))

        # Diversity factor (different types of context)
        type_count = len(set(m.memory.type for m in memories))
        diversity_score = min(type_count / 4.0, 1.0)  # Max of 4 types expected
        factors.append(("diversity", diversity_score, 0.1))

        # Weighted average
        confidence = sum(score * weight for _, score, weight in factors)

        return min(confidence, 1.0)

    def _calculate_context_efficiency(
        self, memories: List[SearchResult], original_memories: List[SearchResult]
    ) -> float:
        """Calculate how efficiently we're using tokens for context"""

        if not memories:
            return 0.0

        # Context value (relevance of included memories)
        total_relevance = sum(m.relevance_score for m in memories)

        # Token cost
        total_tokens = sum(self._estimate_memory_tokens(m) for m in memories)

        # Efficiency = value per token
        return total_relevance / max(total_tokens, 1)

    def _estimate_tokens(self, text: str) -> int:
        """Quick token estimation"""
        return int(len(text.split()) * 1.3)

    async def _get_session_indicators(self, session: SessionContext) -> Dict[str, Any]:
        """Get indicators about the current session"""

        return {
            "files_count": len(session.current_files),
            "has_tests": any("test" in f.lower() for f in session.current_files),
            "has_config": any(
                f.endswith((".json", ".yaml", ".yml", ".toml")) for f in session.current_files
            ),
            "primary_language": self._detect_primary_language(session.current_files),
            "project_areas": self._detect_project_areas(session.current_files),
        }

    def _detect_primary_language(self, files: List[str]) -> str:
        """Detect primary programming language"""

        extensions = {}
        for file in files:
            if "." in file:
                ext = file.split(".")[-1].lower()
                extensions[ext] = extensions.get(ext, 0) + 1

        if not extensions:
            return "unknown"

        return max(extensions.items(), key=lambda x: x[1])[0]

    def _detect_project_areas(self, files: List[str]) -> List[str]:
        """Detect what areas of the project are being worked on"""

        areas = set()

        for file in files:
            file_lower = file.lower()

            if any(term in file_lower for term in ["api", "endpoint", "route"]):
                areas.add("api")
            if any(term in file_lower for term in ["ui", "component", "frontend"]):
                areas.add("frontend")
            if any(term in file_lower for term in ["db", "model", "schema"]):
                areas.add("database")
            if any(term in file_lower for term in ["auth", "security", "login"]):
                areas.add("authentication")
            if any(term in file_lower for term in ["test", "spec"]):
                areas.add("testing")

        return list(areas)

    async def _get_last_active_branch(self) -> Optional[str]:
        """Get the last active git branch"""
        if not self.session_db:
            return None

        last_session = self.session_db.get_last_session()
        return last_session.branch if last_session else None

    async def _get_last_activity_time(self) -> Optional[datetime]:
        """Get timestamp of last activity in project"""
        if not self.session_db:
            return None

        last_session = self.session_db.get_last_session()
        if last_session:
            return last_session.end_time or last_session.start_time
        return None

    async def _get_recent_files(self, hours: int) -> List[str]:
        """Get files that were recently active"""
        if not self.session_db:
            return []

        recent_sessions = self.session_db.get_recent_sessions(hours=hours)
        recent_files = set()
        for session in recent_sessions:
            recent_files.update(session.active_files)

        return list(recent_files)


class AutoInjectionTrigger:
    """Handles automatic triggering of context injection with enhanced session awareness"""

    def __init__(self, injector: SmartContextInjector):
        self.injector = injector
        self.last_injection_time = None
        self.injection_cooldown = timedelta(
            minutes=15
        )  # Reduced cooldown for better responsiveness
        self.adaptive_threshold = 0.6  # Starting threshold

    async def should_trigger_injection(self, session: SessionContext) -> bool:
        """Determine if we should auto-inject context with adaptive intelligence"""

        # Enhanced cooldown with context awareness
        if self.last_injection_time:
            time_since_last = datetime.now() - self.last_injection_time

            # Reduce cooldown if significant context change detected
            if await self._detect_significant_context_change(session):
                cooldown = timedelta(minutes=5)  # Short cooldown for major changes
            else:
                cooldown = self.injection_cooldown

            if time_since_last < cooldown:
                return False

        # Enhanced session detection with multiple signals
        session_boundary_detected = await self.injector.detect_session_start(session)

        if session_boundary_detected:
            return True

        # Additional smart triggers
        return await self._check_additional_triggers(session)

    async def _detect_significant_context_change(self, session: SessionContext) -> bool:
        """Detect if there's been a significant change in context that warrants injection"""

        if not self.injector.session_tracker:
            return False

        try:
            # Check file activity patterns
            current_session = self.injector.session_tracker.current_session
            if current_session:
                # Significant new files added
                current_files = set(session.current_files)
                tracked_files = set(current_session.active_files)

                new_files_ratio = len(current_files - tracked_files) / max(len(current_files), 1)
                if new_files_ratio > 0.5:  # More than 50% new files
                    return True

                # Check for high-value file types
                important_files = [
                    f
                    for f in session.current_files
                    if any(f.endswith(ext) for ext in [".py", ".js", ".ts", ".go", ".java"])
                ]
                if len(important_files) > len(tracked_files):
                    return True

            return False
        except:
            return False

    async def _check_additional_triggers(self, session: SessionContext) -> bool:
        """Check for additional triggers beyond session boundaries"""

        triggers = []

        # File-based triggers
        file_trigger_score = await self._calculate_file_trigger_score(session)
        if file_trigger_score > 0.7:
            triggers.append(("file_activity", file_trigger_score))

        # Time-based triggers with adaptive thresholds
        time_trigger_score = await self._calculate_time_trigger_score(session)
        if time_trigger_score > self.adaptive_threshold:
            triggers.append(("time_pattern", time_trigger_score))

        # Context richness triggers
        context_richness = await self._calculate_context_richness(session)
        if context_richness > 0.8:
            triggers.append(("rich_context", context_richness))

        # Adaptive threshold adjustment
        if triggers:
            max_score = max(score for _, score in triggers)
            self._adjust_adaptive_threshold(max_score)
            return True

        return False

    async def _calculate_file_trigger_score(self, session: SessionContext) -> float:
        """Calculate trigger score based on file activity"""

        if not self.injector.session_db:
            return 0.0

        score = 0.0

        # Check for recently modified files
        for file_path in session.current_files:
            file_sessions = self.injector.session_db.get_file_activity_history(file_path, days=1)
            if file_sessions:
                # Files with recent activity get higher scores
                recent_activity = len(
                    [
                        s
                        for s in file_sessions
                        if (datetime.now() - s.start_time).total_seconds() < 3600
                    ]
                )
                score += min(recent_activity * 0.3, 1.0)

        return min(score, 1.0)

    async def _calculate_time_trigger_score(self, session: SessionContext) -> float:
        """Calculate trigger score based on time patterns"""

        if not self.injector.session_db:
            return 0.5  # Default score

        # Get recent session patterns
        recent_sessions = self.injector.session_db.get_recent_sessions(hours=72)

        if not recent_sessions:
            return 0.7  # High score for first session

        # Calculate time since last meaningful session
        last_session = recent_sessions[0]
        time_gap = datetime.now() - (last_session.end_time or last_session.start_time)

        # Score based on gap duration
        gap_hours = time_gap.total_seconds() / 3600

        if gap_hours > 8:  # Long gap
            return 0.9
        elif gap_hours > 2:  # Medium gap
            return 0.6
        elif gap_hours > 0.5:  # Short gap
            return 0.3
        else:  # Very short gap
            return 0.1

    async def _calculate_context_richness(self, session: SessionContext) -> float:
        """Calculate how much valuable context is available for injection"""

        if not self.injector.session_db:
            return 0.5

        # Check for rich context indicators
        richness_score = 0.0

        # Multiple active files
        file_score = min(len(session.current_files) / 5.0, 1.0)
        richness_score += file_score * 0.3

        # Recent commits
        if session.recent_commits:
            commit_score = min(len(session.recent_commits) / 3.0, 1.0)
            richness_score += commit_score * 0.2

        # Active context threads
        if self.injector.session_db:
            active_threads = self.injector.session_db.get_active_context_threads(limit=3)
            thread_score = min(len(active_threads) / 3.0, 1.0)
            richness_score += thread_score * 0.3

        # Session continuity
        if self.injector.session_tracker:
            current_session = self.injector.session_tracker.current_session
            if current_session:
                continuity_score = current_session.continuity_score
                richness_score += continuity_score * 0.2

        return min(richness_score, 1.0)

    def _adjust_adaptive_threshold(self, observed_score: float):
        """Adjust the adaptive threshold based on observed patterns"""

        # Move threshold towards observed scores to adapt to user patterns
        adjustment_rate = 0.1
        target_threshold = 0.7  # Target to maintain reasonable trigger frequency

        if observed_score > self.adaptive_threshold:
            # User seems to value higher scores, adjust up slightly
            self.adaptive_threshold += (observed_score - self.adaptive_threshold) * adjustment_rate
        else:
            # Adjust back towards target
            self.adaptive_threshold += (
                target_threshold - self.adaptive_threshold
            ) * adjustment_rate

        # Keep within reasonable bounds
        self.adaptive_threshold = max(0.3, min(0.9, self.adaptive_threshold))

    async def trigger_injection(
        self, session: SessionContext, memories: List[SearchResult]
    ) -> Optional[str]:
        """Execute auto-injection and return context string"""

        result = await self.injector.generate_auto_injection(session, memories)

        if result and result.auto_trigger_confidence > 0.6:
            self.last_injection_time = datetime.now()

            logger.info(
                f"Auto-injected context: {result.token_count} tokens, "
                f"{result.memories_included} memories, "
                f"efficiency: {result.context_efficiency_score:.2f}"
            )

            return result.injected_context

        return None
