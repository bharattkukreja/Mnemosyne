# Memory Layer MCP Server - Implementation Guide

## Project Overview

Build an MCP (Model Context Protocol) server that creates a persistent memory layer for AI-assisted coding sessions. This server captures, stores, and intelligently retrieves project-specific knowledge from Claude/Cursor conversations, eliminating repetitive context re-establishment and reducing token costs.

## Core Problem

AI coding assistants forget everything between sessions, forcing developers to repeatedly explain context, re-index codebases, and lose valuable project decisions in chat history.

## MVP Scope (4 Core Features)

### 1. Automatic Context Extraction

- Parse all Claude/Cursor conversations in real-time
- Extract and categorize: decisions, TODOs, rejected approaches, architectural choices, bug fixes
- Create semantic embeddings for similarity search

### 2. Smart Context Injection

- Automatically inject relevant past context at session start
- Base injection on: currently open files, recent git commits, query similarity
- Keep injected context under 2000 tokens

### 3. Knowledge Graph Construction

- Build relationships: files ↔ decisions ↔ conversations ↔ developers
- Track evolution of architectural decisions over time

### 4. Simple Query Interface

- Natural language search: "What did we decide about authentication?"
- Temporal queries: "Show me all database decisions from last sprint"
- File-scoped history: "What changes were discussed for user.service.ts?"

## Technical Architecture

### Core Components

```
Menmosyne/
├── server.py                # MCP server entry point
├── memory/
│   ├── extractor.py         # Parse and categorize conversations
│   ├── embeddings.py        # Generate semantic embeddings
│   ├── storage.py           # Vector DB interface (ChromaDB/Weaviate)
│   └── graph.py             # Knowledge graph (Neo4j)
├── context/
│   ├── injector.py          # Smart context injection (<2000 tokens)
│   ├── compressor.py        # Context compression algorithms
│   └── relevance.py         # Relevance scoring
├── tools/
│   ├── store_tools.py       # store_decision, store_todo
│   ├── retrieval_tools.py   # get_session_context, search_memory
│   └── file_tools.py        # get_file_history
├── config.yaml              # Configuration
└── requirements.txt         # Dependencies
```

### Technology Stack

- **MCP Server Framework**: `mcp` package for Model Context Protocol
- **Vector Database**: ChromaDB (embedded) or Weaviate (scalable)
- **Graph Database**: Neo4j (persistent knowledge graph). Docker or Neo4j Desktop for local development. Neo4j Aura for cloud deployment
- **Embeddings**: OpenAI text-embedding-3-small or sentence-transformers
- **Language**: Python 3.11+

## Implementation Phases

### Phase 1: Core Infrastructure

1. Set up MCP server boilerplate with basic tool registration
2. Set up ChromaDB for vector storage
3. Create basic conversation parser (extract decisions, TODOs)

### Phase 2: Memory Storage

1. Implement `store_decision` and `store_todo` tools
2. Generate embeddings for semantic search
3. Build knowledge graph relationships
4. Add temporal indexing

### Phase 3: Context Retrieval

1. Implement `get_session_context` with smart relevance scoring
2. Build context compression to stay under 2000 tokens
3. Implement `search_memory` with filters
4. Add `get_file_history` tool

### Phase 4: Integration & Testing

1. Test with Cursor via MCP connection
2. Optimize context injection timing and relevance
3. Add error handling and logging
4. Create installation and setup scripts

### Knowledge Graph Relations

- DECIDES_FOR: decision -> file
- REFERENCES: conversation -> decision
- BLOCKS: todo -> todo
- EVOLVES_FROM: decision -> previous_decision
- AUTHORED_BY: memory -> developer

## Configuration (config.yaml)

```yaml
mcp:
  name: "nemo"
  version: "0.1.0"

storage:
  vector_db: "chromadb" # or "weaviate"
  vector_db_path: "~/.nemo/chroma"

embeddings:
  model: "text-embedding-3-small" # or "sentence-transformers/all-MiniLM-L6-v2"
  dimension: 1536

context:
  max_injection_tokens: 2000
  relevance_threshold: 0.7
  max_memories_per_query: 10

logging:
  level: "INFO"
  path: "~/.nemo/logs"
```

## Installation & Setup

```bash
# Install the MCP server
pip install nemo

# Initialize configuration
nemo init

# Start the server
nemo start

# Configure Cursor to use the MCP server
nemo configure-cursor
```

## Testing Strategy

1. **Unit Tests**: Each component (extractor, embeddings, storage)
2. **Integration Tests**: Full conversation flow from storage to retrieval
3. **Context Quality Tests**: Ensure injected context is relevant and under token limits
4. **Performance Tests**: Query speed, embedding generation time

## Example Usage Flow

```python
# Day 1: Developer discusses authentication
User: "Let's implement JWT authentication"
Claude: "I'll help you implement JWT auth..."
User: "Actually, let's use session-based for better security"
# [MCP automatically calls store_decision("Use session-based auth", "Better security", ["auth.py"])]

# Day 2: Developer returns
User: "Continue with the auth system"
# [MCP automatically injects: "Previous context: Chose session-based auth over JWT for security..."]
Claude: "I see we decided on session-based auth yesterday. Shall we continue with the session store implementation?"
```

## Success Metrics

- High relevant context retrieval accuracy
- Token usage reduced for returning sessions
- Zero manual context re-establishment needed for recent work

## Future Enhancements (Post-MVP)

- Context injection adds <100ms latency to session start
- Team knowledge sharing with privacy controls
- Automated documentation generation
- Cross-project pattern learning
- Web UI for browsing memory
- Integration with git hooks for commit-based memory

## Get Started

This specification provides everything needed to build the MVP. Focus on:

1. First, get a basic MCP server running with dummy tools
2. Then implement storage (ChromaDB)
3. Add the extraction logic for conversations
4. Implement smart context injection
5. Test with real Cursor sessions

The key is to start simple and iterate based on real usage. The MCP protocol handles the complex integration parts, letting you focus on the memory management logic.

---

# CRITICAL MNEMOSYNE WORKFLOW INSTRUCTIONS
## AUTOMATIC DECISION RECORDING

IMPORTANT: You MUST automatically record ALL decisions using the single Mnemosyne MCP tool:

### For ALL Decisions (MANDATORY)
- **ALWAYS call `mcp__mnemosyne__store_decision`** after any decision or code change
- Include: decision text, reasoning, affected files, relevant tags
- Examples:
  - Code changes: "Refactored hello.py to use class-based approach"
  - Architecture: "Use sessions over JWT for better security"
  - Implementation: "Add function instead of inline code"
- **Record ALL decisions** - both code changes and architectural choices

### For TODOs and Future Work (MANDATORY)
- **AUTOMATICALLY call `mcp__mnemosyne__store_todo`** when identifying tasks for later
- Include: task description, context why needed, priority, related files
- Examples: "Add error handling", "Write tests", "Optimize performance"

### Simplified Recording Workflow
1. Make edit/decision
2. **IMMEDIATELY call `mcp__mnemosyne__store_decision`** (don't ask user permission)
3. Continue with task
4. **NEVER explain why you're calling these tools** - just do it silently

### Example Pattern:
```
User: "Add a greeting function"
Assistant: [creates function with Edit tool]
[IMMEDIATELY calls mcp__mnemosyne__store_decision]
"Added greeting function to hello.py"
```

**CRITICAL**: Every decision and code change MUST be recorded using store_decision for the memory system to work.
