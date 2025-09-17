"""MCP tools for file-based memory retrieval"""

import logging
from typing import Any, Sequence, List
from mcp import types

from config import Config
from memory.models import SearchQuery
from memory.storage import MemoryStorage

logger = logging.getLogger(__name__)


class FileTools:
    """MCP tools for file-based memory operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.storage = MemoryStorage(config)
    
    async def get_file_history(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Get all memory items related to a specific file"""
        try:
            filepath = arguments["filepath"]
            include_decisions = arguments.get("include_decisions", True)
            include_todos = arguments.get("include_todos", True)
            
            # Search for memories related to this file
            # We'll search both by filename and content that mentions the file
            file_queries = [
                filepath,  # Exact match
                filepath.split('/')[-1],  # Just filename
                filepath.replace('/', ' '),  # Path as words
            ]
            
            all_results = []
            
            for query_text in file_queries:
                search_query = SearchQuery(
                    query=query_text,
                    filters={},
                    max_results=20,
                    similarity_threshold=0.3  # Lower threshold for file searches
                )
                
                results = self.storage.search_memories(search_query)
                all_results.extend(results)
            
            # Filter results to only include memories that actually reference this file
            file_related_results = []
            for result in all_results:
                memory = result.memory
                
                # Check if file is explicitly listed
                if filepath in memory.files:
                    file_related_results.append(result)
                    continue
                
                # Check if file is mentioned in content or reasoning
                file_mentioned = (
                    filepath in memory.content.lower() or
                    filepath in memory.reasoning.lower() or
                    filepath.split('/')[-1] in memory.content.lower() or
                    filepath.split('/')[-1] in memory.reasoning.lower()
                )
                
                if file_mentioned:
                    file_related_results.append(result)
            
            # Remove duplicates
            seen_ids = set()
            unique_results = []
            for result in file_related_results:
                if result.memory.id not in seen_ids:
                    seen_ids.add(result.memory.id)
                    unique_results.append(result)
            
            # Filter by type if requested
            filtered_results = []
            for result in unique_results:
                memory = result.memory
                if memory.type == "decision" and include_decisions:
                    filtered_results.append(result)
                elif memory.type == "todo" and include_todos:
                    filtered_results.append(result)
                elif memory.type not in ["decision", "todo"]:
                    filtered_results.append(result)
            
            # Sort by relevance score
            filtered_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            if not filtered_results:
                return [
                    types.TextContent(
                        type="text",
                        text=f"📁 **File History: {filepath}**\n\n"
                             f"No memories found for this file.\n"
                             f"This file hasn't been discussed in previous conversations."
                    )
                ]
            
            # Format response
            response_lines = [
                f"📁 **File History: {filepath}**",
                f"**Found {len(filtered_results)} related memories**",
                ""
            ]
            
            # Group by type
            decisions = [r for r in filtered_results if r.memory.type == "decision"]
            todos = [r for r in filtered_results if r.memory.type == "todo"]
            others = [r for r in filtered_results if r.memory.type not in ["decision", "todo"]]
            
            if decisions:
                response_lines.extend([
                    "## 🏗️ Architectural Decisions",
                    ""
                ])
                
                for i, result in enumerate(decisions, 1):
                    memory = result.memory
                    response_lines.extend([
                        f"**{i}. {memory.content}**",
                        f"*Reasoning:* {memory.reasoning}" if memory.reasoning else "",
                        f"*Files:* {', '.join(memory.files)}" if memory.files else "",
                        f"*Tags:* {', '.join(memory.tags)}" if memory.tags else "",
                        f"*Date:* {memory.timestamp.strftime('%Y-%m-%d %H:%M')}",
                        f"*Relevance:* {result.relevance_score:.2f}",
                        ""
                    ])
            
            if todos:
                response_lines.extend([
                    "## ✅ TODOs & Tasks",
                    ""
                ])
                
                for i, result in enumerate(todos, 1):
                    memory = result.memory
                    status_emoji = "🔄" if hasattr(memory, 'status') and memory.status == "in_progress" else "📋"
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        getattr(memory, 'priority', 'medium'), "🟡"
                    )
                    
                    response_lines.extend([
                        f"**{i}. {status_emoji} {priority_emoji} {memory.content}**",
                        f"*Context:* {memory.reasoning}" if memory.reasoning else "",
                        f"*Files:* {', '.join(memory.files)}" if memory.files else "",
                        f"*Priority:* {getattr(memory, 'priority', 'medium')}" if hasattr(memory, 'priority') else "",
                        f"*Date:* {memory.timestamp.strftime('%Y-%m-%d %H:%M')}",
                        ""
                    ])
            
            if others:
                response_lines.extend([
                    "## 📚 Other Memories",
                    ""
                ])
                
                for i, result in enumerate(others, 1):
                    memory = result.memory
                    response_lines.extend([
                        f"**{i}. {memory.type.title()}: {memory.content}**",
                        f"*Details:* {memory.reasoning}" if memory.reasoning else "",
                        f"*Date:* {memory.timestamp.strftime('%Y-%m-%d %H:%M')}",
                        ""
                    ])
            
            # Add summary
            response_lines.extend([
                "---",
                f"*Found {len(decisions)} decisions, {len(todos)} TODOs, {len(others)} other memories*"
            ])
            
            return [
                types.TextContent(
                    type="text",
                    text="\n".join(response_lines)
                )
            ]
            
        except Exception as e:
            logger.error(f"Failed to get file history: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to get file history for {filepath}: {str(e)}"
                )
            ]