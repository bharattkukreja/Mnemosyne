"""Automatic trigger mechanism for code context association"""

import asyncio
import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Create dummy classes when watchdog is not available
    class FileSystemEventHandler:
        pass
    class Observer:
        def schedule(self, *args, **kwargs): pass
        def start(self): pass
        def stop(self): pass
        def join(self): pass

from config import Config
from tools.store_tools import StoreTools

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Represents a message in the conversation"""
    content: str
    timestamp: datetime
    source: str = "unknown"  # "user", "assistant", "system"
    tool_calls: List[str] = field(default_factory=list)


@dataclass
class FileChange:
    """Represents a file change event"""
    file_path: str
    change_type: str  # "created", "modified", "deleted"
    timestamp: datetime
    estimated_lines_changed: Optional[int] = None


class ConversationTracker:
    """Tracks conversation messages for context association"""

    def __init__(self, max_messages: int = 100, max_age_hours: int = 24):
        self.max_messages = max_messages
        self.max_age = timedelta(hours=max_age_hours)
        self.messages: deque[ConversationMessage] = deque(maxlen=max_messages)

    def add_message(self, content: str, source: str = "unknown", tool_calls: List[str] = None):
        """Add a message to the conversation history"""
        message = ConversationMessage(
            content=content,
            timestamp=datetime.now(),
            source=source,
            tool_calls=tool_calls or []
        )
        self.messages.append(message)
        self._cleanup_old_messages()

    def get_recent_messages(self, count: Optional[int] = None) -> List[str]:
        """Get recent conversation messages as strings"""
        messages_to_return = list(self.messages)

        if count:
            messages_to_return = messages_to_return[-count:]

        return [f"{msg.source}: {msg.content}" for msg in messages_to_return]

    def get_messages_around_time(self, target_time: datetime, window_minutes: int = 10) -> List[str]:
        """Get messages around a specific time"""
        window = timedelta(minutes=window_minutes)
        relevant_messages = []

        for msg in self.messages:
            if abs(msg.timestamp - target_time) <= window:
                relevant_messages.append(f"{msg.source}: {msg.content}")

        return relevant_messages

    def _cleanup_old_messages(self):
        """Remove messages older than max_age"""
        cutoff_time = datetime.now() - self.max_age
        while self.messages and self.messages[0].timestamp < cutoff_time:
            self.messages.popleft()


class AutoFileWatcher(FileSystemEventHandler):
    """File system watcher for automatic code context association"""

    def __init__(self, auto_trigger: 'AutoTrigger'):
        self.auto_trigger = auto_trigger
        self.ignored_patterns = {
            '.git', '__pycache__', '.DS_Store', '.pyc', '.log',
            'node_modules', '.next', '.vscode', '.idea'
        }
        self.code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs',
            '.java', '.cpp', '.c', '.h', '.swift', '.kt', '.rb',
            '.php', '.scala', '.clj', '.hs', '.ml', '.f90'
        }

    def should_ignore_file(self, file_path: str) -> bool:
        """Check if file should be ignored"""
        path = Path(file_path)

        # Ignore based on patterns
        for pattern in self.ignored_patterns:
            if pattern in str(path):
                return True

        # Only watch code files
        return path.suffix not in self.code_extensions

    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and not self.should_ignore_file(event.src_path):
            change = FileChange(
                file_path=event.src_path,
                change_type="modified",
                timestamp=datetime.now()
            )
            asyncio.create_task(self.auto_trigger.handle_file_change(change))

    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory and not self.should_ignore_file(event.src_path):
            change = FileChange(
                file_path=event.src_path,
                change_type="created",
                timestamp=datetime.now()
            )
            asyncio.create_task(self.auto_trigger.handle_file_change(change))


class AutoTrigger:
    """Automatic trigger system for code context association"""

    def __init__(self, config: Config):
        self.config = config
        self.store_tools = StoreTools(config)
        self.conversation_tracker = ConversationTracker()

        # File watching
        self.observer = None
        self.watch_directory = Path.cwd()  # Watch current working directory

        # Debouncing to avoid duplicate triggers
        self.recent_changes: Dict[str, datetime] = {}
        self.debounce_seconds = 2

        # Integration state
        self.enabled = True

    async def start_watching(self, directory: Optional[str] = None):
        """Start file system watching"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("Watchdog not available - file watching disabled")
            return

        if directory:
            self.watch_directory = Path(directory)

        if not self.watch_directory.exists():
            logger.error(f"Watch directory does not exist: {self.watch_directory}")
            return

        try:
            self.observer = Observer()
            event_handler = AutoFileWatcher(self)
            self.observer.schedule(event_handler, str(self.watch_directory), recursive=True)
            self.observer.start()
            logger.info(f"Started watching directory: {self.watch_directory}")
        except Exception as e:
            logger.error(f"Failed to start file watching: {e}")

    def stop_watching(self):
        """Stop file system watching"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped file watching")

    def add_conversation_message(self, content: str, source: str = "unknown", tool_calls: List[str] = None):
        """Add a message to conversation tracking"""
        self.conversation_tracker.add_message(content, source, tool_calls)

    async def handle_file_change(self, change: FileChange):
        """Handle a detected file change"""
        if not self.enabled:
            return

        # Debounce rapid changes to the same file
        if self._should_debounce(change):
            return

        self.recent_changes[change.file_path] = change.timestamp

        try:
            # Get conversation context based on recent message count instead of time
            # Changed from time-based (5 minutes) to message-count-based (7 messages)
            context_messages = self.conversation_tracker.get_recent_messages(count=7)

            if len(context_messages) < 2:
                logger.debug(f"Insufficient context for {change.file_path} - skipping")
                return

            # Generate edit summary based on file and change type
            edit_summary = self._generate_edit_summary(change)

            # Estimate lines changed (simple heuristic)
            lines_changed = await self._estimate_lines_changed(change)

            # Call associate_code_context
            args = {
                "file_path": change.file_path,
                "edit_summary": edit_summary,
                "conversation_messages": context_messages,
                "edit_type": change.change_type,
                "lines_changed": lines_changed,
                "context_window": 3
            }

            result = await self.store_tools.associate_code_context(args)
            logger.info(f"Auto-associated context for {change.file_path}")

        except Exception as e:
            logger.error(f"Failed to auto-associate context for {change.file_path}: {e}")

    def _should_debounce(self, change: FileChange) -> bool:
        """Check if this change should be debounced"""
        if change.file_path in self.recent_changes:
            last_change = self.recent_changes[change.file_path]
            if (change.timestamp - last_change).total_seconds() < self.debounce_seconds:
                return True
        return False

    def _generate_edit_summary(self, change: FileChange) -> str:
        """Generate a summary of the file edit"""
        file_path = Path(change.file_path)
        file_name = file_path.name

        if change.change_type == "created":
            return f"Created new file {file_name}"
        elif change.change_type == "modified":
            return f"Modified {file_name}"
        elif change.change_type == "deleted":
            return f"Deleted {file_name}"
        else:
            return f"Changed {file_name}"

    async def _estimate_lines_changed(self, change: FileChange) -> Optional[int]:
        """Estimate number of lines changed (simple heuristic)"""
        try:
            file_path = Path(change.file_path)
            if not file_path.exists():
                return None

            # For new files, count total lines
            if change.change_type == "created":
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return sum(1 for _ in f)

            # For modifications, we'd need git diff or file history
            # For now, return None (unknown)
            return None

        except Exception:
            return None


class MCPConversationIntegration:
    """Integration for tracking MCP conversation messages"""

    def __init__(self, auto_trigger: AutoTrigger):
        self.auto_trigger = auto_trigger

    def on_user_message(self, message: str):
        """Called when user sends a message"""
        self.auto_trigger.add_conversation_message(message, "user")

    def on_assistant_message(self, message: str, tool_calls: List[str] = None):
        """Called when assistant responds"""
        self.auto_trigger.add_conversation_message(message, "assistant", tool_calls)

    def on_tool_call(self, tool_name: str, args: Dict[str, Any]):
        """Called when a tool is invoked"""
        tool_msg = f"Tool call: {tool_name}({json.dumps(args, indent=2)})"
        self.auto_trigger.add_conversation_message(tool_msg, "system", [tool_name])