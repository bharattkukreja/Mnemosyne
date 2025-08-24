# Mnemosyne - Automatic Conversation Logger

An MCP (Model Context Protocol) server that automatically logs conversations with Claude.

## Features

- **Automatic logging** of user messages and Claude's responses
- Session-based tracking with unique session IDs
- Real-time console output and persistent JSON Lines file storage
- Conversation statistics and recent message viewing
- Enhanced log format with metadata and message IDs

## Setup

1. Install dependencies:
```bash
source .venv/bin/activate
pip install "mcp[cli]"
```

2. Configure Claude Desktop:
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "conversation-monitor": {
      "command": "/Users/bkukreja/Desktop/Projects/Mnemosyne/.venv/bin/python",
      "args": ["/Users/bkukreja/Desktop/Projects/Mnemosyne/conversation_monitor.py"]
    }
  }
}
```

3. Restart Claude Desktop

## How It Works

Once configured, Claude will have access to logging tools that enable automatic conversation capture:

- `note_user_message(message)` - Logs user messages
- `note_assistant_response(response)` - Logs Claude's responses  
- `quick_log(user_msg, assistant_msg)` - Logs both sides of an exchange
- `conversation_status()` - Shows current session statistics
- `view_recent_conversation(limit)` - Shows recent messages

## Viewing Your Conversations

### 1. Console Output (Real-time)
Run the server directly to see live logging:
```bash
python conversation_monitor.py
```

### 2. Log File
All conversations are saved to `conversation_log.jsonl`:
```bash
cat conversation_log.jsonl
```

### 3. Through Claude
Ask Claude: "Show me our recent conversation" or "What's the conversation status?"

## Enhanced Log Format

```json
{
  "timestamp": "2025-08-22T23:20:35.159616",
  "session_id": "session_20250822_232035", 
  "message_id": 2,
  "role": "user",
  "content": "Hello! Can you help me with Python programming?",
  "metadata": {}
}
```

## Testing

Test the server functionality:
```bash
python test_monitor.py
```

## Usage Tips

To enable automatic logging, ask Claude to use the logging tools:
- "Please note this conversation"
- "Log our discussion" 
- "Keep track of what we're talking about"

Claude will then automatically log the conversation as you interact!