"""MCP tools for storing memories"""

import logging
from typing import Any, Sequence
from mcp import types

from config import Config
from memory.models import Decision, Todo, CodeContext
from memory.extractor import ConversationExtractor
from memory.storage import MemoryStorage

logger = logging.getLogger(__name__)


class StoreTools:
    """MCP tools for storing decisions and TODOs"""

    def __init__(self, config: Config):
        self.config = config
        self.storage = MemoryStorage(config)
        self.extractor = ConversationExtractor()
        self._current_session_id = None

    def set_current_session_id(self, session_id: str):
        """Set the current session ID for linking memories"""
        self._current_session_id = session_id
    
    async def store_decision(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Store an architectural or implementation decision"""
        try:
            decision = arguments["decision"]
            reasoning = arguments["reasoning"]
            files = arguments["files"]
            tags = arguments.get("tags", [])
            
            # Create Decision object
            decision_obj = Decision(
                decision=decision,
                reasoning=reasoning,
                files=files,
                tags=tags,
                session_id=self._current_session_id
            )
            
            # Store in memory system
            memory_id = self.storage.store_memory(decision_obj)
            
            logger.info(f"Stored decision {memory_id}: {decision}")
            
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Decision stored successfully!\n\n"
                         f"**ID:** {memory_id}\n"
                         f"**Decision:** {decision}\n"
                         f"**Reasoning:** {reasoning}\n"
                         f"**Files:** {', '.join(files)}\n"
                         f"**Tags:** {', '.join(tags) if tags else 'None'}\n"
                         f"**Timestamp:** {decision_obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            ]
            
        except Exception as e:
            logger.error(f"Failed to store decision: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to store decision: {str(e)}"
                )
            ]
    
    async def store_todo(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Store a TODO item with context"""
        try:
            task = arguments["task"]
            context = arguments["context"]
            priority = arguments.get("priority", "medium")
            files = arguments.get("files", [])
            
            # Create Todo object
            todo_obj = Todo(
                task=task,
                context=context,
                priority=priority,
                files=files,
                session_id=self._current_session_id
            )
            
            # Store in memory system
            memory_id = self.storage.store_memory(todo_obj)
            
            logger.info(f"Stored TODO {memory_id}: {task}")
            
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ TODO stored successfully!\n\n"
                         f"**ID:** {memory_id}\n"
                         f"**Task:** {task}\n"
                         f"**Context:** {context}\n"
                         f"**Priority:** {priority}\n"
                         f"**Files:** {', '.join(files) if files else 'None'}\n"
                         f"**Status:** {todo_obj.status}\n"
                         f"**Timestamp:** {todo_obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            ]
            
        except Exception as e:
            logger.error(f"Failed to store TODO: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to store TODO: {str(e)}"
                )
            ]

