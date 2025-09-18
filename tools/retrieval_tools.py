"""MCP tools for retrieving memories"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Sequence

from mcp import types

from config import Config
from context.compressor import ContextCompressor
from context.relevance import RelevanceScorer
from context.smart_injector import AutoInjectionTrigger, SessionContext, SmartContextInjector
from memory.models import SearchQuery
from memory.storage import MemoryStorage

logger = logging.getLogger(__name__)


class RetrievalTools:
    """MCP tools for searching and retrieving memories"""

    def __init__(self, config: Config):
        self.config = config
        self.storage = MemoryStorage(config)
        self.relevance_scorer = RelevanceScorer()
        self.context_compressor = ContextCompressor(config.context.max_injection_tokens)

        # Initialize smart context injection
        config_dict = {
            "auto_inject_max_tokens": 800,
            "auto_inject_confidence": 0.7,
            "min_context_efficiency": 0.5,
        }
        self.smart_injector = SmartContextInjector(config_dict)
        self.auto_trigger = AutoInjectionTrigger(self.smart_injector)

    async def search_memory(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Search through stored memories"""
        try:
            query_text = arguments["query"]
            filters = arguments.get("filters", {})

            # Create search query
            search_query = SearchQuery(
                query=query_text,
                filters=filters,
                max_results=self.config.context.max_memories_per_query,
                similarity_threshold=self.config.context.relevance_threshold,
            )

            # Search memories
            results = self.storage.search_memories(search_query)

            # Improve relevance scoring
            query_context = {"intent": "search", "tags": self._extract_query_tags(query_text)}
            results = self.relevance_scorer.score_memories(results, query_context)

            if not results:
                return [
                    types.TextContent(
                        type="text",
                        text=f"🔍 **Search Results for:** '{query_text}'\n\n"
                        f"No memories found matching your query.\n"
                        f"**Filters:** {filters}",
                    )
                ]

            # Format results
            response_lines = [
                f"🔍 **Search Results for:** '{query_text}'",
                f"**Found {len(results)} memories**",
                "",
            ]

            for i, result in enumerate(results, 1):
                memory = result.memory
                score = result.similarity_score

                response_lines.extend(
                    [
                        f"**{i}. {memory.type.title()} ({score:.2f} similarity)**",
                        f"**Content:** {memory.content}",
                        f"**Reasoning:** {memory.reasoning}" if memory.reasoning else "",
                        f"**Files:** {', '.join(memory.files)}" if memory.files else "",
                        f"**Tags:** {', '.join(memory.tags)}" if memory.tags else "",
                        f"**Created:** {memory.timestamp.strftime('%Y-%m-%d %H:%M')}",
                        f"**ID:** {memory.id}",
                        "",
                    ]
                )

            # Add filter info
            if filters:
                response_lines.append(f"**Applied filters:** {filters}")

            return [types.TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [types.TextContent(type="text", text=f"❌ Search failed: {str(e)}")]

    async def get_session_context(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Get relevant context for current session with smart auto-injection"""
        try:
            current_files = arguments["current_files"]
            recent_commits = arguments.get("recent_commits", [])
            max_tokens = arguments.get("max_tokens", self.config.context.max_injection_tokens)
            auto_inject = arguments.get("auto_inject", True)  # Enable smart injection by default

            # Create session context
            session = SessionContext(
                current_files=current_files,
                recent_commits=recent_commits,
                active_branch=self._get_current_git_branch(),
                project_root=str(Path.cwd()),
                session_start_time=datetime.now(),
                working_directory=str(Path.cwd()),
                recent_file_changes=self._get_recent_file_changes(),
            )

            # Get all memories first
            all_memories = self.storage.get_all_memories()

            # Check if we should auto-inject smart context
            if auto_inject and await self.auto_trigger.should_trigger_injection(session):
                smart_context = await self.auto_trigger.trigger_injection(session, all_memories)
                if smart_context:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"🎯 **Smart Context Auto-Injected**\n\n{smart_context}\n\n*This context was automatically selected based on your current files and recent activity. It uses ~{len(smart_context.split()) * 1.3:.0f} tokens to save you from manually re-establishing context.*",
                        )
                    ]

            # Fall back to traditional context retrieval
            file_context = " ".join(current_files)
            commit_context = " ".join(recent_commits) if recent_commits else ""

            # Search for relevant memories
            context_query = f"{file_context} {commit_context}".strip()

            if not context_query:
                return [
                    types.TextContent(
                        type="text",
                        text="📋 **Session Context**\n\nNo context to search for. Provide files or commits.",
                    )
                ]

            search_query = SearchQuery(
                query=context_query,
                max_results=5,  # Limit for context injection
                similarity_threshold=0.3,  # Lower threshold for context
            )

            results = self.storage.search_memories(search_query)

            # Improve relevance scoring for context
            query_context = {
                "current_files": current_files,
                "recent_commits": recent_commits,
                "intent": "context",
            }
            results = self.relevance_scorer.score_memories(results, query_context)

            # Use smart context compression
            context_response = self.context_compressor.compress_session_context(
                results, current_files, recent_commits, max_tokens
            )

            return [types.TextContent(type="text", text=context_response)]

        except Exception as e:
            logger.error(f"Failed to get session context: {e}")
            return [
                types.TextContent(type="text", text=f"❌ Failed to get session context: {str(e)}")
            ]

    def _extract_query_tags(self, query_text: str) -> List[str]:
        """Extract relevant tags from search query"""
        tags = []
        query_lower = query_text.lower()

        # Technology tags
        if any(word in query_lower for word in ["api", "endpoint", "rest", "graphql"]):
            tags.append("api")
        if any(word in query_lower for word in ["database", "db", "sql", "postgres", "mongo"]):
            tags.append("database")
        if any(word in query_lower for word in ["frontend", "ui", "react", "vue", "angular"]):
            tags.append("frontend")
        if any(word in query_lower for word in ["backend", "server", "express", "fastapi"]):
            tags.append("backend")
        if any(word in query_lower for word in ["auth", "security", "permission", "jwt"]):
            tags.append("security")
        if any(word in query_lower for word in ["test", "testing", "unit", "integration"]):
            tags.append("testing")
        if any(word in query_lower for word in ["performance", "speed", "optimize"]):
            tags.append("performance")

        return tags

    async def get_smart_context(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Get ultra-efficient smart context for session start"""
        try:
            current_files = arguments.get("current_files", [])
            force_inject = arguments.get("force", False)

            if not current_files:
                # Try to detect current files from working directory
                current_files = self._detect_current_files()

            # Create session context
            session = SessionContext(
                current_files=current_files,
                recent_commits=self._get_recent_commits(),
                active_branch=self._get_current_git_branch(),
                project_root=str(Path.cwd()),
                session_start_time=datetime.now(),
                working_directory=str(Path.cwd()),
                recent_file_changes=self._get_recent_file_changes(),
            )

            # Get all memories
            all_memories = self.storage.get_all_memories()

            if not all_memories:
                return [
                    types.TextContent(
                        type="text",
                        text="📝 No memories stored yet. Start coding and decisions will be automatically captured!",
                    )
                ]

            # Force smart injection or check if needed
            should_inject = force_inject or await self.auto_trigger.should_trigger_injection(
                session
            )

            if should_inject:
                smart_context = await self.auto_trigger.trigger_injection(session, all_memories)
                if smart_context:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"🚀 **Smart Context Ready**\n\n{smart_context}\n\n💡 *Optimized context using {len(smart_context.split()) * 1.3:.0f} tokens. This replaces having to manually search through {len(all_memories)} stored memories.*",
                        )
                    ]

            # No injection needed
            recent_count = len(
                [m for m in all_memories if (datetime.now() - m.memory.timestamp).days < 7]
            )
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ **No context injection needed**\n\nCurrent session doesn't require historical context. You have {len(all_memories)} total memories ({recent_count} recent). Use `force: true` to inject anyway.",
                )
            ]

        except Exception as e:
            logger.error(f"Smart context failed: {e}")
            return [types.TextContent(type="text", text=f"❌ Smart context failed: {str(e)}")]

    def _get_current_git_branch(self) -> str:
        """Get current git branch"""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "branch", "--show-current"], capture_output=True, text=True, cwd=Path.cwd()
            )
            return result.stdout.strip() if result.returncode == 0 else "main"
        except:
            return "main"

    def _get_recent_commits(self) -> List[str]:
        """Get recent git commits"""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "log", "--oneline", "-5"], capture_output=True, text=True, cwd=Path.cwd()
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
        except:
            pass
        return []

    def _get_recent_file_changes(self) -> List[str]:
        """Get recently changed files"""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
        except:
            pass
        return []

    def _detect_current_files(self) -> List[str]:
        """Auto-detect files being worked on"""
        current_dir = Path.cwd()

        # Look for common development files
        common_files = []

        # Python files
        for py_file in current_dir.glob("*.py"):
            common_files.append(str(py_file.relative_to(current_dir)))

        # JavaScript/TypeScript files
        for js_file in current_dir.glob("*.{js,ts,jsx,tsx}"):
            common_files.append(str(js_file.relative_to(current_dir)))

        # Configuration files
        for config_file in current_dir.glob("*.{json,yaml,yml,toml}"):
            common_files.append(str(config_file.relative_to(current_dir)))

        # Return first few files
        return common_files[:5]
