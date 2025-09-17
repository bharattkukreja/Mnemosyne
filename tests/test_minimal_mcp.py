#!/usr/bin/env python3
"""Minimal MCP server test"""

import asyncio
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Create server
server = Server("test-server")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="test_tool",
            description="A simple test tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Test message"
                    }
                },
                "required": ["message"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls"""
    if name == "test_tool":
        return [
            types.TextContent(
                type="text",
                text=f"Test tool called with: {arguments.get('message', 'no message')}"
            )
        ]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())