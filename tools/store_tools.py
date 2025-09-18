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
                tags=tags
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
                files=files
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

    async def associate_code_context(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Associate code changes with conversation context"""
        try:
            file_path = arguments["file_path"]
            edit_summary = arguments["edit_summary"]
            conversation_messages = arguments["conversation_messages"]
            edit_position = arguments.get("edit_position", len(conversation_messages) - 1)
            edit_type = arguments.get("edit_type", "modify")
            lines_changed = arguments.get("lines_changed")
            context_window = arguments.get("context_window", 3)

            # Extract code context using the conversation extractor
            code_context = self.extractor.extract_code_context(
                conversation_messages=conversation_messages,
                edit_position=edit_position,
                file_path=file_path,
                edit_summary=edit_summary,
                edit_type=edit_type,
                lines_changed=lines_changed,
                context_window=context_window
            )

            # Store in memory system
            memory_id = self.storage.store_memory(code_context)

            logger.info(f"Stored code context {memory_id} for {file_path}")

            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Code context associated successfully!\n\n"
                         f"**ID:** {memory_id}\n"
                         f"**File:** {file_path}\n"
                         f"**Edit:** {edit_summary}\n"
                         f"**Type:** {edit_type}\n"
                         f"**Lines Changed:** {lines_changed or 'Unknown'}\n"
                         f"**Context Window:** {context_window} messages\n"
                         f"**Tags:** {', '.join(code_context.tags) if code_context.tags else 'None'}\n"
                         f"**Timestamp:** {code_context.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            ]

        except Exception as e:
            logger.error(f"Failed to associate code context: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to associate code context: {str(e)}"
                )
            ]