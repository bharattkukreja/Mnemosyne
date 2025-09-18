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

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.relevance_scorer = RelevanceScorer()
        self.compressor = ContextCompressor()

        # Efficiency-focused settings
        self.max_auto_inject_tokens = config.get("auto_inject_max_tokens", 800)  # Conservative
        self.confidence_threshold = config.get("auto_inject_confidence", 0.7)
        self.min_context_efficiency = config.get("min_context_efficiency", 0.5)

    async def detect_session_start(self, current_session: SessionContext) -> bool:
        """Detect if this is a new session that needs context injection"""

        # Indicators of new session:
        # 1. First activity in project today
        # 2. Branch switch
        # 3. New files opened
        # 4. Long time gap since last activity

        indicators = []

        # Check for branch switch
        last_branch = await self._get_last_active_branch()
        if last_branch and last_branch != current_session.active_branch:
            indicators.append(("branch_switch", 0.8))

        # Check for time gap
        last_activity = await self._get_last_activity_time()
        if last_activity:
            time_gap = current_session.session_start_time - last_activity
            if time_gap > timedelta(hours=4):
                indicators.append(("long_gap", 0.7))
            elif time_gap > timedelta(hours=1):
                indicators.append(("medium_gap", 0.5))

        # Check for new files
        recent_files = await self._get_recent_files(hours=24)
        new_files = [f for f in current_session.current_files if f not in recent_files]
        if new_files:
            indicators.append(("new_files", 0.6))

        # Calculate confidence
        if not indicators:
            return False

        confidence = max(score for _, score in indicators)
        return confidence >= self.confidence_threshold

    async def generate_auto_injection(
        self, session: SessionContext, all_memories: List[SearchResult]
    ) -> Optional[InjectionResult]:
        """Generate optimal context injection for session start"""

        # Step 1: Get highly relevant memories
        relevant_memories = await self._get_session_relevant_memories(session, all_memories)

        if not relevant_memories:
            return None

        # Step 2: Optimize for maximum context per token
        optimized_context = await self._optimize_context_density(relevant_memories, session)

        # Step 3: Calculate efficiency metrics
        efficiency_score = self._calculate_context_efficiency(optimized_context, relevant_memories)

        if efficiency_score < self.min_context_efficiency:
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
        """Get memories most relevant to current session"""

        # Enhanced query context with session info
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
        high_relevance = [m for m in scored_memories if m.relevance_score > 0.6]

        return high_relevance[:15]  # Limit candidates

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

        # Boost based on content type importance
        content_boosts = {
            "decision": 2.0,  # High value - prevents re-discussion
            "rejected_approach": 1.8,  # High value - prevents re-doing work
            "architecture": 1.5,  # Medium value - structural understanding
            "bug_fix": 1.2,  # Medium value - prevents repeated bugs
            "todo": 0.8,  # Lower value for auto-injection
        }

        value *= content_boosts.get(memory.memory.type, 1.0)

        # Boost for file overlap
        file_overlap = len(set(memory.memory.files) & set(session.current_files))
        value += file_overlap * 0.3

        # Boost for recent activity
        age_hours = (datetime.now() - memory.memory.timestamp).total_seconds() / 3600
        if age_hours < 24:
            value += 0.5
        elif age_hours < 168:  # 1 week
            value += 0.2

        return value

    def _estimate_memory_tokens(self, memory: SearchResult) -> int:
        """Estimate tokens for compressed memory format"""

        # Use compressed format for estimation
        compressed = self._get_compressed_format(memory)
        return len(compressed.split()) * 1.3  # Rough token estimate

    def _get_compressed_format(self, memory: SearchResult) -> str:
        """Ultra-compressed format for auto-injection"""

        # Ultra-minimal format to maximize content/token ratio
        content = memory.memory.content
        if len(content) > 60:
            content = content[:57] + "..."

        reasoning = memory.memory.reasoning
        if reasoning and len(reasoning) > 40:
            reasoning = reasoning[:37] + "..."

        # Essential info only
        parts = [content]

        if reasoning:
            parts.append(f"({reasoning})")

        if memory.memory.files:
            # Only show most relevant file
            relevant_file = memory.memory.files[0]
            if "/" in relevant_file:
                relevant_file = relevant_file.split("/")[-1]  # Just filename
            parts.append(f"[{relevant_file}]")

        return " ".join(parts)

    async def _build_efficient_injection(
        self, memories: List[SearchResult], session: SessionContext
    ) -> Dict[str, Any]:
        """Build the most token-efficient injection"""

        if not memories:
            return {"content": "", "tokens": 0, "confidence": 0.0}

        # Ultra-minimal header
        lines = [f"# Context ({len(memories)} items):"]

        # Group by type for efficiency
        by_type = {}
        for memory in memories:
            mem_type = memory.memory.type
            if mem_type not in by_type:
                by_type[mem_type] = []
            by_type[mem_type].append(memory)

        # Add each type with minimal formatting
        type_labels = {
            "decision": "Decisions",
            "rejected_approach": "Avoided",
            "architecture": "Architecture",
            "bug_fix": "Fixes",
            "todo": "TODOs",
        }

        for mem_type, type_memories in by_type.items():
            if len(type_memories) > 0:
                label = type_labels.get(mem_type, mem_type.title())
                lines.append(
                    f"{label}: {', '.join(self._get_compressed_format(m) for m in type_memories[:3])}"
                )

        content = "\n".join(lines)

        # Calculate confidence based on relevance and coverage
        avg_relevance = sum(m.relevance_score for m in memories) / len(memories)
        file_coverage = len(set().union(*(m.memory.files for m in memories))) / max(
            len(session.current_files), 1
        )
        confidence = (avg_relevance + file_coverage) / 2

        return {
            "content": content,
            "tokens": self._estimate_tokens(content),
            "confidence": confidence,
        }

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
        # This would be implemented with git integration
        # For now, return None
        return None

    async def _get_last_activity_time(self) -> Optional[datetime]:
        """Get timestamp of last activity in project"""
        # This would track last MCP activity
        # For now, return None
        return None

    async def _get_recent_files(self, hours: int) -> List[str]:
        """Get files that were recently active"""
        # This would track recent file activity
        # For now, return empty list
        return []


class AutoInjectionTrigger:
    """Handles automatic triggering of context injection"""

    def __init__(self, injector: SmartContextInjector):
        self.injector = injector
        self.last_injection_time = None
        self.injection_cooldown = timedelta(minutes=30)  # Prevent spam

    async def should_trigger_injection(self, session: SessionContext) -> bool:
        """Determine if we should auto-inject context"""

        # Cooldown check
        if (
            self.last_injection_time
            and datetime.now() - self.last_injection_time < self.injection_cooldown
        ):
            return False

        # Session start detection
        return await self.injector.detect_session_start(session)

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
