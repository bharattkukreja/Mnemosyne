#!/usr/bin/env python3
"""
Mnemosyne MCP Server - Memory Layer for AI Coding Sessions
"""

import asyncio
import logging
from typing import Any, Sequence

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from config import load_config, ensure_directories

# Load configuration
try:
    config = load_config()
    ensure_directories(config)
except Exception as e:
    logging.error(f"Failed to load configuration: {e}")
    raise

# Configure logging
logging.basicConfig(level=getattr(logging, config.logging.level))
logger = logging.getLogger("mnemosyne")

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
                    "decision": {
                        "type": "string",
                        "description": "The decision that was made"
                    },
                    "reasoning": {
                        "type": "string", 
                        "description": "The reasoning behind the decision"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files related to this decision"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorizing the decision",
                        "default": []
                    }
                },
                "required": ["decision", "reasoning", "files"]
            }
        ),
        types.Tool(
            name="store_todo",
            description="Store a TODO item with context",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The task to be done"
                    },
                    "context": {
                        "type": "string",
                        "description": "Context around why this task is needed"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Priority level",
                        "default": "medium"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files related to this TODO",
                        "default": []
                    }
                },
                "required": ["task", "context"]
            }
        ),
        types.Tool(
            name="search_memory",
            description="Search through stored memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "filters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["decision", "todo", "all"],
                                "default": "all"
                            },
                            "files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by specific files"
                            }
                        },
                        "default": {}
                    }
                },
                "required": ["query"]
            }
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
                        "description": "Files currently being worked on"
                    },
                    "recent_commits": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recent git commits",
                        "default": []
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens for context",
                        "default": 2000
                    }
                },
                "required": ["current_files"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
    """Handle tool calls with dummy implementations for now"""
    
    if name == "store_decision":
        decision = arguments["decision"]
        reasoning = arguments["reasoning"] 
        files = arguments["files"]
        tags = arguments.get("tags", [])
        
        logger.info(f"Storing decision: {decision}")
        return [
            types.TextContent(
                type="text",
                text=f"✅ Decision stored successfully!\n\nDecision: {decision}\nReasoning: {reasoning}\nFiles: {', '.join(files)}\nTags: {', '.join(tags) if tags else 'None'}"
            )
        ]
    
    elif name == "store_todo":
        task = arguments["task"]
        context = arguments["context"]
        priority = arguments.get("priority", "medium")
        files = arguments.get("files", [])
        
        logger.info(f"Storing TODO: {task}")
        return [
            types.TextContent(
                type="text", 
                text=f"✅ TODO stored successfully!\n\nTask: {task}\nContext: {context}\nPriority: {priority}\nFiles: {', '.join(files) if files else 'None'}"
            )
        ]
    
    elif name == "search_memory":
        query = arguments["query"]
        filters = arguments.get("filters", {})
        
        logger.info(f"Searching memory: {query}")
        return [
            types.TextContent(
                type="text",
                text=f"🔍 Search results for: '{query}'\n\nFilters: {filters}\n\n(No memories stored yet - this is a dummy implementation)"
            )
        ]
    
    elif name == "get_session_context":
        current_files = arguments["current_files"]
        recent_commits = arguments.get("recent_commits", [])
        max_tokens = arguments.get("max_tokens", 2000)
        
        logger.info(f"Getting session context for files: {current_files}")
        return [
            types.TextContent(
                type="text",
                text=f"📋 Session Context\n\nCurrent files: {', '.join(current_files)}\nRecent commits: {', '.join(recent_commits) if recent_commits else 'None'}\nMax tokens: {max_tokens}\n\n(No context available yet - this is a dummy implementation)"
            )
        ]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server"""
    logger.info("Starting Mnemosyne MCP Server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())