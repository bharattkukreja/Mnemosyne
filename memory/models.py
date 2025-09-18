"""Data models for Mnemosyne memory system"""

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import uuid


class Memory(BaseModel):
    """Base memory item"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["decision", "todo", "bug_fix", "rejected_approach", "architecture", "code_context"]
    content: str
    reasoning: str = ""
    files: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    conversation_id: Optional[str] = None
    developer_id: Optional[str] = None
    embedding: Optional[List[float]] = None


class Decision(Memory):
    """Architectural or implementation decision"""
    type: Literal["decision"] = "decision"
    decision: str
    alternatives_considered: Optional[List[str]] = None
    
    def __init__(self, **data):
        if 'content' not in data and 'decision' in data:
            data['content'] = data['decision']
        super().__init__(**data)


class Todo(Memory):
    """TODO item with context"""
    type: Literal["todo"] = "todo"
    task: str
    priority: Literal["low", "medium", "high"] = "medium"
    context: str = ""
    status: Literal["pending", "in_progress", "completed"] = "pending"
    
    def __init__(self, **data):
        if 'content' not in data and 'task' in data:
            data['content'] = data['task']
        if 'reasoning' not in data and 'context' in data:
            data['reasoning'] = data['context']
        super().__init__(**data)


class BugFix(Memory):
    """Bug fix record"""
    type: Literal["bug_fix"] = "bug_fix"
    bug_description: str
    solution: str
    symptoms: Optional[List[str]] = None
    
    def __init__(self, **data):
        if 'content' not in data and 'bug_description' in data:
            data['content'] = data['bug_description']
        if 'reasoning' not in data and 'solution' in data:
            data['reasoning'] = data['solution']
        super().__init__(**data)


class SearchQuery(BaseModel):
    """Search query parameters"""
    query: str
    filters: dict = Field(default_factory=dict)
    max_results: int = 10
    similarity_threshold: float = 0.7


class CodeContext(Memory):
    """Code change with associated conversation context"""
    type: Literal["code_context"] = "code_context"
    file_path: str
    edit_summary: str
    conversation_context: str
    edit_type: Literal["create", "modify", "delete"] = "modify"
    lines_changed: Optional[int] = None

    def __init__(self, **data):
        if 'content' not in data and 'edit_summary' in data:
            data['content'] = data['edit_summary']
        if 'reasoning' not in data and 'conversation_context' in data:
            data['reasoning'] = data['conversation_context']
        if 'files' not in data and 'file_path' in data:
            data['files'] = [data['file_path']]
        super().__init__(**data)


class SearchResult(BaseModel):
    """Search result item"""
    memory: Memory
    similarity_score: float
    relevance_score: float