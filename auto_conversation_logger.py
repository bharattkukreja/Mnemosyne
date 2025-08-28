#!/usr/bin/env python3
"""
Enhanced MCP server for automatic conversation logging with Claude.
Captures all interactions automatically using request/response hooks.
"""

import asyncio
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Log file path
LOG_FILE = Path("auto_conversation_log.jsonl")

class ConversationLogger:
    def __init__(self):
        self.session_id = None
        self.message_count = 0
    
    def log_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Log a message to both console and file."""
        timestamp = datetime.datetime.now().isoformat()
        self.message_count += 1
        
        # Log entry
        log_entry = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "message_id": self.message_count,
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        # Print to console
        print(f"[{timestamp}] {role.upper()}: {content}")
        
        # Append to log file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

# Initialize logger
logger = ConversationLogger()

# Create the server
server = Server("AutoConversationLogger")

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="get_conversation_log",
            description="Get the current conversation log",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of recent messages to return",
                        "default": 50
                    }
                }
            }
        ),
        types.Tool(
            name="clear_conversation_log",
            description="Clear the conversation log",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_conversation_stats",
            description="Get conversation statistics",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> List[types.TextContent]:
    """Handle tool calls and log them automatically."""
    arguments = arguments or {}
    
    # Log the tool call as a user action
    logger.log_message("user", f"Called tool: {name}", {"arguments": arguments})
    
    if name == "get_conversation_log":
        limit = arguments.get("limit", 50)
        try:
            messages = []
            if LOG_FILE.exists():
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        if line.strip():
                            messages.append(json.loads(line))
            
            response = json.dumps(messages, indent=2)
            # Log the assistant response
            logger.log_message("assistant", f"Retrieved {len(messages)} conversation messages")
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            error_msg = f"Error retrieving conversation log: {e}"
            logger.log_message("assistant", error_msg)
            return [types.TextContent(type="text", text=error_msg)]
    
    elif name == "clear_conversation_log":
        try:
            LOG_FILE.unlink(missing_ok=True)
            logger.message_count = 0
            response = "Conversation log cleared successfully"
            logger.log_message("assistant", response)
            return [types.TextContent(type="text", text=response)]
        except Exception as e:
            error_msg = f"Error clearing log: {e}"
            logger.log_message("assistant", error_msg)
            return [types.TextContent(type="text", text=error_msg)]
    
    elif name == "get_conversation_stats":
        try:
            stats = {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "session_id": logger.session_id,
                "log_file": str(LOG_FILE.absolute())
            }
            
            if LOG_FILE.exists():
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            stats["total_messages"] += 1
                            if entry["role"] == "user":
                                stats["user_messages"] += 1
                            elif entry["role"] == "assistant":
                                stats["assistant_messages"] += 1
            
            response = json.dumps(stats, indent=2)
            logger.log_message("assistant", f"Generated conversation statistics")
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            error_msg = f"Error generating stats: {e}"
            logger.log_message("assistant", error_msg)
            return [types.TextContent(type="text", text=error_msg)]
    
    else:
        error_msg = f"Unknown tool: {name}"
        logger.log_message("assistant", error_msg)
        return [types.TextContent(type="text", text=error_msg)]

@server.list_resources()
async def handle_list_resources() -> List[types.Resource]:
    """List available resources."""
    return [
        types.Resource(
            uri="conversation://current",
            name="Current Conversation",
            description="Live view of the current conversation log",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a resource and log the access."""
    logger.log_message("user", f"Requested resource: {uri}")
    
    if uri == "conversation://current":
        try:
            messages = []
            if LOG_FILE.exists():
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            messages.append(json.loads(line))
            
            result = json.dumps(messages, indent=2)
            logger.log_message("assistant", f"Provided current conversation log ({len(messages)} messages)")
            return result
            
        except Exception as e:
            error_msg = f"Error reading conversation resource: {e}"
            logger.log_message("assistant", error_msg)
            return json.dumps({"error": error_msg})
    
    error_msg = f"Unknown resource: {uri}"
    logger.log_message("assistant", error_msg)
    return json.dumps({"error": error_msg})

async def main():
    """Main server function."""
    # Generate session ID
    logger.session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.log_message("system", f"Started conversation logging session: {logger.session_id}")
    
    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="AutoConversationLogger",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())