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
from tools.store_tools import StoreTools
from tools.retrieval_tools import RetrievalTools
from tools.file_tools import FileTools

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

# Initialize tools
store_tools = StoreTools(config)
retrieval_tools = RetrievalTools(config)
file_tools = FileTools(config)

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
        ),
        types.Tool(
            name="get_file_history",
            description="Get all memory items related to a specific file",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to get history for"
                    },
                    "include_decisions": {
                        "type": "boolean",
                        "description": "Include architectural decisions",
                        "default": True
                    },
                    "include_todos": {
                        "type": "boolean", 
                        "description": "Include TODO items",
                        "default": True
                    }
                },
                "required": ["filepath"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
    """Handle tool calls with real implementations"""
    
    try:
        if name == "store_decision":
            return await store_tools.store_decision(arguments)
        
        elif name == "store_todo":
            return await store_tools.store_todo(arguments)
        
        elif name == "search_memory":
            return await retrieval_tools.search_memory(arguments)
        
        elif name == "get_session_context":
            return await retrieval_tools.get_session_context(arguments)
        
        elif name == "get_file_history":
            return await file_tools.get_file_history(arguments)
        
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Tool call failed for {name}: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"❌ Tool '{name}' failed: {str(e)}"
            )
        ]


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