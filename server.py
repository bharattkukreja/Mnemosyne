#!/usr/bin/env python3
"""
Mnemosyne MCP Server - Memory Layer for AI Coding Sessions
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Sequence

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from config import ensure_directories, load_config
from tools.file_tools import FileTools
from tools.graph_tools import GraphTools
from tools.retrieval_tools import RetrievalTools
from tools.store_tools import StoreTools

# Configure logging early
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("mnemosyne")

# Load configuration
try:
    # Ensure we resolve config.yaml relative to this file, not the CWD used by the launcher (e.g., Claude)
    CONFIG_PATH = str(Path(__file__).with_name("config.yaml"))
    config = load_config(CONFIG_PATH)
    ensure_directories(config)
except Exception as e:
    logging.error(f"Failed to load configuration: {e}")
    raise

# Initialize tools directly
store_tools = StoreTools(config)
retrieval_tools = RetrievalTools(config)
file_tools = FileTools(config)
graph_tools = GraphTools(config)

# Create the MCP server
server = Server("mnemosyne")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available MCP tools"""
    return [
        types.Tool(
            name="store_decision",
            description="Store an architectural or implementation decision",
            inputSchema={
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "description": "The decision that was made"},
                    "reasoning": {
                        "type": "string",
                        "description": "The reasoning behind the decision",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files related to this decision",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorizing the decision",
                        "default": [],
                    },
                },
                "required": ["decision", "reasoning", "files"],
            },
        ),
        types.Tool(
            name="store_todo",
            description="Store a TODO item with context",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The task to be done"},
                    "context": {
                        "type": "string",
                        "description": "Context around why this task is needed",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Priority level",
                        "default": "medium",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files related to this TODO",
                        "default": [],
                    },
                },
                "required": ["task", "context"],
            },
        ),
        types.Tool(
            name="search_memory",
            description="Search through stored memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "filters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["decision", "todo", "all"],
                                "default": "all",
                            },
                            "files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by specific files",
                            },
                        },
                        "default": {},
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_session_context",
            description="Get relevant context for current session",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files currently being worked on",
                    },
                    "recent_commits": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recent git commits",
                        "default": [],
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens for context",
                        "default": 2000,
                    },
                },
                "required": ["current_files"],
            },
        ),
        types.Tool(
            name="get_file_history",
            description="Get all memory items related to a specific file",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to get history for",
                    },
                    "include_decisions": {
                        "type": "boolean",
                        "description": "Include architectural decisions",
                        "default": True,
                    },
                    "include_todos": {
                        "type": "boolean",
                        "description": "Include TODO items",
                        "default": True,
                    },
                },
                "required": ["filepath"],
            },
        ),
        types.Tool(
            name="explore_relationships",
            description="Explore knowledge graph relationships around a memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to explore relationships for",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum relationship depth to explore",
                        "default": 2,
                    },
                },
                "required": ["memory_id"],
            },
        ),
        types.Tool(
            name="analyze_decision_impact",
            description="Analyze the impact and influence of a specific decision",
            inputSchema={
                "type": "object",
                "properties": {
                    "decision_id": {
                        "type": "string",
                        "description": "ID of the decision to analyze",
                    }
                },
                "required": ["decision_id"],
            },
        ),
        types.Tool(
            name="discover_patterns",
            description="Discover knowledge patterns and insights from the memory graph",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        types.Tool(
            name="trace_file_evolution",
            description="Trace the chronological evolution of decisions for a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to trace evolution for",
                    }
                },
                "required": ["filepath"],
            },
        ),
    ]


def wrap_result(result: Any, tool_name: str) -> list[types.TextContent]:
    """
    Ensure every tool call result is converted into a valid MCP response.
    - If it's already a list of TextContent → return as is
    - If it's a string → wrap it
    - If it's something else (dict, etc.) → stringify it
    """
    if isinstance(result, list) and all(isinstance(x, types.TextContent) for x in result):
        return result
    if isinstance(result, str):
        return [types.TextContent(type="text", text=result)]
    if result is None:
        return [types.TextContent(type="text", text=f"ℹ️ {tool_name} returned no result")]
    return [types.TextContent(type="text", text=str(result))]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
    """Handle tool calls with real implementations"""

    try:
        if name == "store_decision":
            return wrap_result(await store_tools.store_decision(arguments), name)

        elif name == "store_todo":
            return wrap_result(await store_tools.store_todo(arguments), name)

        elif name == "search_memory":
            return wrap_result(await retrieval_tools.search_memory(arguments), name)

        elif name == "get_session_context":
            return wrap_result(await retrieval_tools.get_session_context(arguments), name)

        elif name == "get_file_history":
            return wrap_result(await file_tools.get_file_history(arguments), name)

        elif name == "explore_relationships":
            return wrap_result(await graph_tools.explore_relationships(arguments), name)

        elif name == "analyze_decision_impact":
            return wrap_result(await graph_tools.analyze_decision_impact(arguments), name)

        elif name == "discover_patterns":
            return wrap_result(await graph_tools.discover_patterns(arguments), name)

        elif name == "trace_file_evolution":
            return wrap_result(await graph_tools.trace_file_evolution(arguments), name)

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Tool call failed for {name}: {e}")
        return [types.TextContent(type="text", text=f"❌ Tool '{name}' failed: {str(e)}")]


async def main():
    """Run the MCP server"""
    logger.info("Starting Mnemosyne MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
