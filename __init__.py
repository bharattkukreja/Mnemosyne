"""
Mnemosyne - Memory Layer MCP Server for AI Coding Sessions

A Model Context Protocol (MCP) server that provides persistent memory
for AI-assisted coding sessions, capturing and retrieving architectural
decisions, TODOs, and project context.
"""

__version__ = "0.1.0"
__author__ = "Bharatt Kukreja"
__email__ = "kukrejabharatt@gmail.com"

from .config import Config, load_config
from .memory.embeddings import EmbeddingGenerator
from .memory.extractor import ConversationExtractor
from .memory.graph import KnowledgeGraph
from .memory.models import Decision, Memory, SearchQuery, SearchResult, Todo
from .memory.storage import MemoryStorage

__all__ = [
    "Config",
    "load_config",
    "Memory",
    "Decision",
    "Todo",
    "SearchQuery",
    "SearchResult",
    "MemoryStorage",
    "EmbeddingGenerator",
    "KnowledgeGraph",
    "ConversationExtractor",
]
