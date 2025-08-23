#!/usr/bin/env python3
"""
Simple conversation logger MCP server with robust JSON handling.
"""

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Simple Conversation Logger")

# Log file path - use absolute path to ensure it's always accessible
LOG_FILE = Path("/Users/bkukreja/Desktop/Projects/Mnemosyne/conversation_log.jsonl")

def safe_log_message(role: str, content: str) -> None:
    """Safely log a message with error handling."""
    try:
        timestamp = datetime.datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "role": role,
            "content": str(content)
        }
        
        # Print to console
        print(f"[{timestamp}] {role.upper()}: {content}")
        
        # Append to log file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Logging error: {e}")

@mcp.tool()
def log_message(role: str, message: str) -> str:
    """Log a message from user or assistant."""
    print(f"DEBUG: log_message called with role='{role}', message='{message[:100]}...'")
    safe_log_message(role, message)
    print(f"DEBUG: Message logged to {LOG_FILE}")
    return f"✓ Logged {role} message to {LOG_FILE.name}"

@mcp.tool()
def log_exchange(user_message: str, assistant_message: str) -> str:
    """Log both user and assistant messages."""
    safe_log_message("user", user_message)
    safe_log_message("assistant", assistant_message)
    return "Exchange logged"

@mcp.tool()
def get_recent_messages(limit: int = 5) -> str:
    """Get recent messages as formatted text."""
    try:
        messages = []
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        entry = json.loads(line)
                        messages.append(f"[{entry['role']}] {entry['content']}")
        
        return "\n".join(messages) if messages else "No messages found"
    
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def clear_log() -> str:
    """Clear the conversation log."""
    try:
        LOG_FILE.unlink(missing_ok=True)
        return "Log cleared"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    safe_log_message("system", "Simple conversation logger started")
    mcp.run()