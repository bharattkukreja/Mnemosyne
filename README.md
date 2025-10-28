# Mnemosyne

> **Never lose context again.** A persistent memory layer for AI-assisted coding sessions.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Server-green.svg)](https://modelcontextprotocol.io/)

## Overview

Mnemosyne is an MCP (Model Context Protocol) server that creates a persistent memory layer for AI coding assistants like Claude in Cursor. It captures, stores, and intelligently retrieves project-specific knowledge from conversations, eliminating repetitive context re-establishment and reducing token costs.

### The Problem

AI coding assistants forget everything between sessions. Developers must repeatedly:
- Re-explain project context and decisions
- Re-establish architectural patterns
- Re-index codebases
- Lose valuable decisions buried in chat history

### The Solution

Mnemosyne automatically:
- **Captures decisions** as you make them in conversations
- **Builds a knowledge graph** connecting files, decisions, and TODOs
- **Injects smart context** when you return to work
- **Preserves architectural reasoning** across sessions and team members

## Features

### Core Capabilities

- **Automatic Decision Recording** - Stores architectural choices and implementation decisions
- **Smart Context Injection** - Auto-injects relevant past context based on current files
- **Knowledge Graph** - Tracks relationships between files, decisions, and conversations
- **Semantic Search** - Natural language queries to find past decisions
- **File History** - Complete timeline of decisions affecting each file
- **TODO Tracking** - Captures and manages action items with context

### 14 MCP Tools

| Tool | Purpose |
|------|---------|
| `store_decision` | Store architectural or implementation decisions |
| `store_todo` | Capture TODO items with context |
| `update_todo_status` | Update TODO status (pending/in_progress/completed/obsolete) |
| `search_memory` | Search through stored memories with filters |
| `get_session_context` | Get relevant context for current work |
| `get_file_history` | View complete decision history for a file |
| `explore_relationships` | Navigate knowledge graph connections |
| `analyze_decision_impact` | Analyze ripple effects of decisions |
| `discover_patterns` | Find knowledge patterns and insights |
| `trace_file_evolution` | Chronological timeline of file decisions |
| `start_auto_recording` | Enable automatic change recording |
| `record_conversation_message` | Record conversation context |
| `get_smart_context` | Ultra-efficient context for session start |
| `get_past_context` | Resume from last completed session |

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Cursor IDE** or **Claude Desktop**
- **Git** (for version tracking features)
- **Docker** (for Neo4j) or Neo4j Desktop

### Installation

#### 1. Clone and Install

```bash
git clone https://github.com/bharattkukreja/mnemosyne.git
cd mnemosyne
pip install -r requirements.txt
```

This installs all required dependencies including:
- **ChromaDB** - Vector database for semantic search
- **sentence-transformers** - For generating embeddings
- **neo4j driver** - For knowledge graph connections
- **MCP server** - Model Context Protocol implementation

ChromaDB will automatically initialize its storage in `~/.mnemosyne/chroma` when you first run the server.

#### 2. Set Up Neo4j

Mnemosyne requires Neo4j for its knowledge graph capabilities. Choose one option:

**Option A: Docker (Recommended)**
```bash
docker run -d \
  --name mnemosyne-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/mnemosyne \
  -v neo4j_data:/data \
  neo4j:latest
```

**Option B: Neo4j Desktop**
1. Download from [https://neo4j.com/desktop/](https://neo4j.com/desktop/)
2. Create a new database
3. Set password to `mnemosyne` (or customize in config.yaml)
4. Start the database

Verify Neo4j is running:
```bash
# Neo4j Browser should be accessible at http://localhost:7474
```

#### 3. Configure for Cursor

```bash
# Initialize configuration
python cli.py init

# Configure Cursor integration
python cli.py configure-cursor

# Verify installation
python cli.py status
```

#### 4. Configure for Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python",
      "args": ["/absolute/path/to/mnemosyne/server.py"]
    }
  }
}
```

#### 5. Restart Your IDE

Restart Cursor or Claude Desktop to load the MCP server.

### Cursor-Specific Configuration

For Cursor users, Mnemosyne includes a `.cursorrules` file that optimizes Claude's behavior with the MCP tools. This file makes Claude:

- Proactively call Mnemosyne tools instead of just explaining them
- Automatically suggest context retrieval when you open files
- Store decisions during architectural discussions
- Be more action-oriented with memory operations

**The `.cursorrules` file is already included** and will work automatically in Cursor. You can customize it to match your workflow preferences.

### Verification

```bash
python cli.py status
```

Expected output:
```
✅ Configuration: Valid
✅ Storage directory: ~/.mnemosyne
✅ ChromaDB: Initialized at ~/.mnemosyne/chroma
✅ Neo4j: Connected
✅ Cursor integration: Configured
📦 Dependencies: Available
💾 Stored memories: 0
```

If Neo4j shows as disconnected, verify it's running and check your `config.yaml` credentials.

## Usage Examples

### Storing Decisions

```
Developer: "Let's use PostgreSQL instead of MongoDB for better transaction support"
Claude: I'll store this architectural decision.

[Calls: store_decision(
  decision="Use PostgreSQL instead of MongoDB",
  reasoning="Better transaction support and ACID compliance needed",
  files=["database/config.py", "requirements.txt"],
  tags=["database", "architecture"]
)]

✅ Decision stored successfully!
```

### Auto-Context Injection

```
Developer: [Opens components/UserProfile.tsx]

[Mnemosyne auto-calls: get_session_context(["components/UserProfile.tsx"])]

Claude: "I see you're working on UserProfile. Previously we decided to use
TypeScript strict mode and implement authentication with JWT tokens..."
```

### Searching Past Decisions

```
Developer: "What did we decide about authentication?"

[Calls: search_memory("authentication security decisions")]

Found 3 memories:
1. Decision: Use JWT tokens for API authentication (2024-01-15)
2. Decision: Store sessions in Redis for fast lookup (2024-01-20)
3. TODO: Implement token refresh mechanism (High priority)
```

### Tracking File History

```
Developer: "Show me the history of changes to database/models.py"

[Calls: get_file_history("database/models.py")]

File history for database/models.py:
📅 2024-01-15 - Decision: Use PostgreSQL with SQLAlchemy ORM
📅 2024-01-18 - Decision: Add database indexes for performance
📅 2024-01-20 - TODO: Implement soft deletes for user records
```

### Knowledge Graph Exploration

```
Developer: "How does our authentication decision connect to other choices?"

[Calls: explore_relationships(auth_decision_id, max_depth=2)]

Relationships for "Use JWT authentication":
→ DECIDES_FOR: auth/middleware.py
→ DEPENDS_ON: Decision "Use Redis for session storage"
→ BLOCKS: TODO "Implement refresh tokens"
→ EVOLVES_FROM: Decision "Rejected session cookies approach"
```

## Architecture

### Technology Stack

- **MCP Server**: `mcp` package for Model Context Protocol
- **Vector Database**: ChromaDB for semantic search and embeddings
- **Graph Database**: Neo4j for knowledge graph and relationship tracking
- **Embeddings**: sentence-transformers (local) or OpenAI API
- **Language**: Python 3.11+

### Storage Architecture

```
Mnemosyne/
├── server.py                # MCP server entry point
├── memory/
│   ├── storage.py           # Vector DB and file storage
│   ├── embeddings.py        # Semantic embeddings
│   ├── graph.py             # Neo4j knowledge graph
│   ├── extractor.py         # Conversation parsing
│   └── auto_trigger.py      # Auto-recording system
├── context/
│   ├── smart_injector.py    # Smart context injection
│   ├── compressor.py        # Context compression
│   └── relevance.py         # Relevance scoring
├── tools/
│   ├── store_tools.py       # Storage MCP tools
│   ├── retrieval_tools.py   # Retrieval MCP tools
│   ├── file_tools.py        # File history tools
│   └── graph_tools.py       # Knowledge graph tools
└── config.yaml              # Configuration
```

### Data Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Cursor/Claude  │◄──►│  MCP Protocol    │◄──►│   Mnemosyne     │
│                 │    │   (stdio)        │    │   Server        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Storage Layer  │
                                               │                 │
                                               │ • Vector Search │
                                               │ • Knowledge Graph│
                                               │ • File Backup   │
                                               └─────────────────┘
```

## Configuration

### Basic Configuration

Edit `config.yaml` to customize:

```yaml
mcp:
  name: "mnemosyne"
  version: "0.1.0"

storage:
  vector_db: "chromadb"
  vector_db_path: "~/.mnemosyne/chroma"

  # Neo4j connection (required for knowledge graph)
  neo4j_uri: "bolt://localhost:7687"
  neo4j_user: "neo4j"
  neo4j_password: "mnemosyne"  # Change if you used a different password

embeddings:
  model: "sentence-transformers/all-MiniLM-L6-v2"
  dimension: 384

context:
  max_injection_tokens: 2000
  relevance_threshold: 0.7
  max_memories_per_query: 10

logging:
  level: "INFO"
  path: "~/.mnemosyne/logs"
```

**Important:** Update the `neo4j_password` in `config.yaml` if you used a different password during Neo4j setup.

## Development Workflow

### Before Mnemosyne
```
Day 1: "Let's use FastAPI for better performance"
Day 7: "Why did we choose FastAPI again?"
       → Lost in chat history, need to re-explain context
```

### With Mnemosyne
```
Day 1: Decision automatically stored with reasoning
Day 7: Context auto-injected when working on API files
       → "I see we chose FastAPI for better performance..."
```

### Team Benefits

- **Onboarding**: New developers get instant context on project decisions
- **Knowledge Sharing**: Decisions persist across team members
- **Consistency**: Similar patterns emerge from shared memory
- **Documentation**: Automatic capture of architectural reasoning

## CLI Commands

```bash
# Initialize configuration
python cli.py init

# Configure Cursor integration
python cli.py configure-cursor

# Start MCP server (for testing)
python cli.py start

# Check installation status
python cli.py status

# Remove from Cursor
python cli.py uninstall
```

### Database Explorer

Mnemosyne includes an interactive database explorer for visualizing and analyzing stored memories:

```bash
# Launch the interactive explorer
python explore_db.py
```

**Features:**
- 📊 Database overview - See counts of memories, nodes, and relationships
- 🗃️ ChromaDB explorer - View vector storage, search by content
- 🕸️ Neo4j explorer - Navigate knowledge graph, explore relationships
- 🔍 Semantic search - Find memories by natural language queries
- 📈 Pattern analysis - Discover knowledge patterns and trends
- 💾 Data export - Export ChromaDB and Neo4j data to JSON
- 🎯 Query templates - Pre-built Neo4j Browser queries for visualization

**Example Usage:**
```bash
$ python explore_db.py

🧠 Mnemosyne Database Explorer
==================================================

📋 What would you like to explore?
1. 📊 Database Overview
2. 🗃️  ChromaDB Data (Vector Storage)
3. 🕸️  Neo4j Data (Knowledge Graph)
4. 🔍 Search Memories
5. 🔗 View Relationships
6. 📈 Analyze Patterns
7. 💾 Export Data
8. 🎯 Neo4j Browser Queries
q. ❌ Quit

Enter your choice (1-8, q to quit):
```

This tool is perfect for:
- Understanding what's in your knowledge base
- Debugging memory storage and retrieval
- Visualizing connections between decisions and files
- Exporting data for analysis or backup

## Troubleshooting

### MCP Server Not Found

1. Restart Cursor/Claude Desktop after configuration
2. Verify server path in MCP config is absolute
3. Check Python is in PATH

### Storage Initialization Failed

1. Check permissions on `~/.mnemosyne/` directory
2. Ensure sufficient disk space
3. Verify Python package installations

### Neo4j Connection Failed

1. Verify Neo4j is running:
   ```bash
   docker ps  # Should show mnemosyne-neo4j container
   # OR check Neo4j Desktop status
   ```

2. Test connection:
   ```bash
   python -c "from neo4j import GraphDatabase; GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'mnemosyne')).verify_connectivity()"
   ```

3. Common fixes:
   - Check firewall settings for port 7687
   - Ensure password in `config.yaml` matches Neo4j password
   - Restart Neo4j container: `docker restart mnemosyne-neo4j`
   - Check Neo4j logs: `docker logs mnemosyne-neo4j`

### Check Logs

```bash
tail -f ~/.mnemosyne/logs/mnemosyne.log
```

## Performance

- **Context Injection**: <1.5 seconds
- **Search Queries**: <500ms (with caching)
- **Storage**: Minimal overhead (async operations)
- **Memory**: ~200MB baseline (varies with data)

### Optimization Tips

For large codebases:
```yaml
context:
  max_injection_tokens: 1500  # Reduce for faster context
  max_memories_per_query: 5   # Limit search results
```

For better search quality:
```yaml
embeddings:
  model: "sentence-transformers/all-mpnet-base-v2"
  dimension: 768

context:
  relevance_threshold: 0.8  # Higher threshold
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

### Development Setup

```bash
# Clone repository
git clone https://github.com/bharattkukreja/mnemosyne.git
cd mnemosyne

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Powered by [ChromaDB](https://www.trychroma.com/) and [Neo4j](https://neo4j.com/)
- Embeddings via [sentence-transformers](https://www.sbert.net/)

## Support

- **Issues**: [GitHub Issues](https://github.com/bharattkukreja/mnemosyne/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bharattkukreja/mnemosyne/discussions)

---

**Never lose context again.** Start using Mnemosyne today and transform how you work with AI coding assistants.
