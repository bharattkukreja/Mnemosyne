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

        # Session tracking removed - simplified approach
        self.current_session_id: Optional[str] = None

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

        # Auto-start session if needed
        if not self.current_session_id:
            self.start_session()

    def start_session(self, current_files: Optional[List[str]] = None) -> str:
        """Start a new coding session"""
        try:
            # Generate simple session ID
            import uuid
            self.current_session_id = str(uuid.uuid4())

            # Link session to store tools
            self.store_tools.set_current_session_id(self.current_session_id)

            logger.info(f"Started session {self.current_session_id}")
            return self.current_session_id

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            # Generate fallback session ID
            import uuid
            self.current_session_id = str(uuid.uuid4())
            self.store_tools.set_current_session_id(self.current_session_id)
            return self.current_session_id

    def end_session(self, context_summary: Optional[str] = None):
        """End the current coding session"""
        if self.current_session_id:
            logger.info(f"Ended session {self.current_session_id}")
            self.current_session_id = None

    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID"""
        return self.current_session_id

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

            # If no explicit conversation context, infer context from file changes
            if len(context_messages) < 2:
                context_messages = await self._infer_context_from_changes(change)
                if not context_messages:
                    logger.debug(f"No context available for {change.file_path} - skipping")
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

    async def _infer_context_from_changes(self, change: FileChange) -> List[str]:
        """Infer conversation context when no explicit messages are available"""
        try:
            file_path = Path(change.file_path)
            context_messages = []

            # Add file change context
            context_messages.append(f"system: File change detected - {change.change_type} {file_path.name}")

            # Try to extract content insights for created/modified files
            if change.change_type in ["created", "modified"] and file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Extract meaningful context from file content
                    if len(content) > 0:
                        # For small files, include a snippet
                        if len(content) < 500:
                            context_messages.append(f"assistant: Working with file content: {content[:200]}...")
                        else:
                            # Extract function/class names or other structural elements
                            lines = content.split('\n')
                            key_lines = []
                            for line in lines[:20]:  # Check first 20 lines
                                stripped = line.strip()
                                if any(keyword in stripped for keyword in ['def ', 'class ', 'function ', 'const ', 'let ', 'var ', 'import ', 'from ', 'export']):
                                    key_lines.append(stripped)

                            if key_lines:
                                context_messages.append(f"assistant: Code structure detected: {'; '.join(key_lines[:3])}")

                except Exception as e:
                    logger.debug(f"Could not read file content for context: {e}")

            # Try to get git context if available
            try:
                import subprocess
                git_log = subprocess.run(
                    ['git', 'log', '--oneline', '-5'],
                    capture_output=True, text=True, timeout=5
                )
                if git_log.returncode == 0:
                    recent_commits = git_log.stdout.strip().split('\n')[:2]
                    for commit in recent_commits:
                        if commit.strip():
                            context_messages.append(f"system: Recent git activity: {commit}")
            except:
                pass  # Git not available or other error

            return context_messages if len(context_messages) >= 2 else []

        except Exception as e:
            logger.error(f"Failed to infer context from changes: {e}")
            return []

    def _detect_current_files(self) -> List[str]:
        """Detect files currently being worked on"""
        current_dir = self.watch_directory
        files = []

        # Look for recently modified code files
        for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs']:
            for file_path in current_dir.glob(f"**/*{ext}"):
                if self._is_recently_modified(file_path):
                    files.append(str(file_path.relative_to(current_dir)))

        return files[:10]  # Limit to 10 files

    def _is_recently_modified(self, file_path: Path) -> bool:
        """Check if file was modified recently (within 1 hour)"""
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            return (datetime.now() - mtime) < timedelta(hours=1)
        except:
            return False

    def _get_current_git_branch(self) -> str:
        """Get current git branch"""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True, text=True, cwd=self.watch_directory
            )
            return result.stdout.strip() if result.returncode == 0 else "main"
        except:
            return "main"

    def _get_recent_commits(self) -> List[str]:
        """Get recent git commits"""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'log', '--oneline', '-5'],
                capture_output=True, text=True, cwd=self.watch_directory
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
        except:
            pass
        return []


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