"""MCP tools for retrieving memories"""

import logging
from typing import Any, Sequence, List
from mcp import types

from config import Config
from memory.models import SearchQuery
from memory.storage import MemoryStorage

logger = logging.getLogger(__name__)


class RetrievalTools:
    """MCP tools for searching and retrieving memories"""
    
    def __init__(self, config: Config):
        self.config = config
        self.storage = MemoryStorage(config)
    
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
                similarity_threshold=self.config.context.relevance_threshold
            )
            
            # Search memories
            results = self.storage.search_memories(search_query)
            
            if not results:
                return [
                    types.TextContent(
                        type="text",
                        text=f"🔍 **Search Results for:** '{query_text}'\n\n"
                             f"No memories found matching your query.\n"
                             f"**Filters:** {filters}"
                    )
                ]
            
            # Format results
            response_lines = [
                f"🔍 **Search Results for:** '{query_text}'",
                f"**Found {len(results)} memories**",
                ""
            ]
            
            for i, result in enumerate(results, 1):
                memory = result.memory
                score = result.similarity_score
                
                response_lines.extend([
                    f"**{i}. {memory.type.title()} ({score:.2f} similarity)**",
                    f"**Content:** {memory.content}",
                    f"**Reasoning:** {memory.reasoning}" if memory.reasoning else "",
                    f"**Files:** {', '.join(memory.files)}" if memory.files else "",
                    f"**Tags:** {', '.join(memory.tags)}" if memory.tags else "",
                    f"**Created:** {memory.timestamp.strftime('%Y-%m-%d %H:%M')}",
                    f"**ID:** {memory.id}",
                    ""
                ])
            
            # Add filter info
            if filters:
                response_lines.append(f"**Applied filters:** {filters}")
            
            return [
                types.TextContent(
                    type="text",
                    text="\n".join(response_lines)
                )
            ]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Search failed: {str(e)}"
                )
            ]
    
    async def get_session_context(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Get relevant context for current session"""
        try:
            current_files = arguments["current_files"]
            recent_commits = arguments.get("recent_commits", [])
            max_tokens = arguments.get("max_tokens", self.config.context.max_injection_tokens)
            
            # Build context query based on current files
            file_context = " ".join(current_files)
            commit_context = " ".join(recent_commits) if recent_commits else ""
            
            # Search for relevant memories
            context_query = f"{file_context} {commit_context}".strip()
            
            if not context_query:
                return [
                    types.TextContent(
                        type="text",
                        text="📋 **Session Context**\n\nNo context to search for. Provide files or commits."
                    )
                ]
            
            search_query = SearchQuery(
                query=context_query,
                max_results=5,  # Limit for context injection
                similarity_threshold=0.3  # Lower threshold for context
            )
            
            results = self.storage.search_memories(search_query)
            
            if not results:
                return [
                    types.TextContent(
                        type="text",
                        text=f"📋 **Session Context**\n\n"
                             f"**Current files:** {', '.join(current_files)}\n"
                             f"**Recent commits:** {', '.join(recent_commits) if recent_commits else 'None'}\n\n"
                             f"No relevant historical context found."
                    )
                ]
            
            # Build context response
            context_lines = [
                "📋 **Session Context**",
                f"**Current files:** {', '.join(current_files)}",
                f"**Recent commits:** {', '.join(recent_commits) if recent_commits else 'None'}",
                "",
                "**Relevant previous decisions and context:**",
                ""
            ]
            
            for result in results:
                memory = result.memory
                context_lines.extend([
                    f"• **{memory.type.title()}:** {memory.content}",
                    f"  *{memory.reasoning}*" if memory.reasoning else "",
                    f"  Files: {', '.join(memory.files)}" if memory.files else "",
                    f"  ({memory.timestamp.strftime('%Y-%m-%d')})",
                    ""
                ])
            
            # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
            estimated_tokens = len("\n".join(context_lines)) // 4
            context_lines.append(f"*Context size: ~{estimated_tokens} tokens*")
            
            return [
                types.TextContent(
                    type="text",
                    text="\n".join(context_lines)
                )
            ]
            
        except Exception as e:
            logger.error(f"Failed to get session context: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to get session context: {str(e)}"
                )
            ]