# Mnemosyne Installation & Cursor Integration Guide

## Quick Start

### 1. Install Mnemosyne
```bash
# Clone the repository
git clone https://github.com/your-org/mnemosyne-mcp.git
cd mnemosyne-mcp

# Install dependencies
pip install -r requirements.txt

# Initialize configuration
python cli.py init
```

### 2. Configure Cursor Integration
```bash
# Automatically configure Cursor
python cli.py configure-cursor

# Check status
python cli.py status
```

### 3. Start Using
1. Restart Cursor
2. Open any project
3. Start a chat with Claude
4. Try: `store_decision("Use React for frontend", "Better component architecture", ["src/App.js"])`

## Detailed Installation

### Prerequisites
- **Python 3.11+**
- **Cursor IDE** (latest version)
- **Optional**: Neo4j for knowledge graphs
- **Optional**: Better embeddings with sentence-transformers

### Step 1: Environment Setup

#### Option A: Virtual Environment (Recommended)
```bash
python -m venv mnemosyne-env
source mnemosyne-env/bin/activate  # On Windows: mnemosyne-env\Scripts\activate
pip install -r requirements.txt
```

#### Option B: System-wide Installation
```bash
pip install -r requirements.txt
```

### Step 2: Configuration

#### Basic Configuration
```bash
python cli.py init
```

This creates `~/.mnemosyne/` with:
- Vector storage (ChromaDB or file-based)
- Configuration files
- Log directories

#### Advanced Configuration
Edit `config.yaml` for custom settings:

```yaml
mcp:
  name: "mnemosyne"
  version: "0.1.0"

storage:
  vector_db: "chromadb"  # or "file" for simple storage
  vector_db_path: "~/.mnemosyne/chroma"
  # Neo4j settings (optional)
  graph_db: "neo4j"
  neo4j_uri: "bolt://localhost:7687"
  neo4j_user: "neo4j"
  neo4j_password: "your_password"

embeddings:
  model: "sentence-transformers/all-MiniLM-L6-v2"  # or OpenAI
  dimension: 384

context:
  max_injection_tokens: 2000
  relevance_threshold: 0.7
  max_memories_per_query: 10

logging:
  level: "INFO"
  path: "~/.mnemosyne/logs"
```

### Step 3: Cursor Integration

#### Automatic Configuration
```bash
python cli.py configure-cursor
```

This automatically adds Mnemosyne to Cursor's MCP configuration.

#### Manual Configuration
If automatic configuration fails, manually edit Cursor's MCP settings:

**Location**: 
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`
- Windows: `%APPDATA%\Cursor\User\globalStorage\rooveterinaryinc.roo-cline\settings\cline_mcp_settings.json`
- Linux: `~/.config/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`

**Add this configuration**:
```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python",
      "args": ["/path/to/mnemosyne/server.py"],
      "env": {},
      "capabilities": ["tools"]
    }
  }
}
```

### Step 4: Verification

#### Check Installation
```bash
python cli.py status
```

Expected output:
```
✅ Configuration: Valid
✅ Storage directory: /Users/you/.mnemosyne
✅ Cursor integration: Configured
📦 Dependencies:
   ✅ MCP Protocol: Available
   ✅ Vector Database: Available
   ✅ Embeddings: Available
   ⚠️  Knowledge Graph: Missing (optional)
   ✅ Configuration: Available
💾 Stored memories: 0
```

#### Test MCP Server
```bash
python cli.py start
# Should show: "Starting Mnemosyne MCP Server..."
# Ctrl+C to stop
```

## Optional Enhancements

### Neo4j Knowledge Graph (Recommended)

#### Install Neo4j
```bash
# Option 1: Docker (easiest)
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest

# Option 2: Neo4j Desktop
# Download from https://neo4j.com/desktop/

# Option 3: Cloud (Neo4j Aura)
# Sign up at https://console.neo4j.io/
```

#### Configure Neo4j
Update `config.yaml`:
```yaml
storage:
  neo4j_uri: "bolt://localhost:7687"  # or your cloud URI
  neo4j_user: "neo4j"
  neo4j_password: "your_password"
```

Test connection:
```bash
python cli.py status
# Should show: ✅ Neo4j: Connected
```

### Better Embeddings

#### Install sentence-transformers
```bash
pip install sentence-transformers torch
```

#### Configure embeddings model
Update `config.yaml`:
```yaml
embeddings:
  model: "sentence-transformers/all-MiniLM-L6-v2"  # Fast, good quality
  # or "sentence-transformers/all-mpnet-base-v2"   # Slower, better quality
  dimension: 384  # or 768 for mpnet
```

## Usage in Cursor

### Available MCP Tools

Once configured, Claude in Cursor has access to 9 tools:

#### Storage Tools
- `store_decision(decision, reasoning, files, tags)` - Store architectural decisions
- `store_todo(task, context, priority, files)` - Store TODO items

#### Search Tools  
- `search_memory(query, filters)` - Search through memories
- `get_session_context(current_files, recent_commits)` - Get relevant context

#### File Tools
- `get_file_history(filepath)` - Get memory history for a specific file

#### Graph Tools (if Neo4j enabled)
- `explore_relationships(memory_id, max_depth)` - Explore memory connections
- `analyze_decision_impact(decision_id)` - Analyze decision ripple effects
- `discover_patterns()` - Find knowledge patterns
- `trace_file_evolution(filepath)` - Trace file's decision timeline

### Example Usage

#### Store a Decision
```
User: "Let's use FastAPI instead of Flask for better performance"
Claude: I'll store this architectural decision.

*Claude calls: store_decision(
  decision="Use FastAPI instead of Flask",
  reasoning="Better performance and automatic OpenAPI docs", 
  files=["api/main.py", "requirements.txt"],
  tags=["architecture", "api", "performance"]
)*

Decision stored successfully! ID: abc123...
```

#### Get Context for Current Work
```
User: *Opens database/models.py*
Claude: *Automatically calls get_session_context(["database/models.py"])*

Found relevant context:
• Decision: Use PostgreSQL for production (2024-01-15)
• TODO: Add database indexes for performance (High priority)
• Decision: Use SQLAlchemy ORM for database layer
```

#### Search Previous Decisions
```
User: "What did we decide about authentication?"
Claude: *Calls search_memory("authentication security")*

Found 3 memories:
1. Decision: Use JWT tokens for API auth
2. TODO: Implement token refresh mechanism  
3. Decision: Store sessions in Redis for fast lookup
```

## Troubleshooting

### Common Issues

#### "MCP server not found"
- Restart Cursor after configuration
- Check that server.py path is correct in MCP config
- Verify Python is in PATH

#### "Storage initialization failed"
- Check permissions on `~/.mnemosyne/` directory
- Ensure sufficient disk space
- Check Python package installations

#### "Neo4j connection failed"
- Verify Neo4j is running: `docker ps` or check Neo4j Desktop
- Test connection: `python -c "from neo4j import GraphDatabase; GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password')).verify_connectivity()"`
- Check firewall settings for port 7687

#### "Embeddings model download failed"
- Ensure internet connection for first download
- Check available disk space (models are ~400MB)
- Try different model in config.yaml

### Performance Optimization

#### For Large Codebases
```yaml
context:
  max_injection_tokens: 1500  # Reduce for faster context
  max_memories_per_query: 5   # Limit search results

storage:
  vector_db: "chromadb"       # Better than file storage for large datasets
```

#### For Better Search Quality
```yaml
embeddings:
  model: "sentence-transformers/all-mpnet-base-v2"  # Better quality
  dimension: 768

context:
  relevance_threshold: 0.8  # Higher threshold for better matches
```

### Getting Help

#### Check Logs
```bash
tail -f ~/.mnemosyne/logs/mnemosyne.log
```

#### Debug Mode
```bash
# Edit config.yaml
logging:
  level: "DEBUG"

# Restart server and check logs
```

#### Validate Installation
```bash
python cli.py status
python -c "import mnemosyne; print('✅ Import successful')"
```

## Advanced Configuration

### Team Usage

For team environments, consider:

1. **Shared Neo4j Instance**:
```yaml
storage:
  neo4j_uri: "bolt://shared-neo4j-server:7687"
```

2. **Developer Identification**:
```yaml
developer:
  id: "your-email@company.com"  # Automatically added to memories
```

3. **Project-specific Storage**:
```yaml
storage:
  vector_db_path: "~/.mnemosyne/projects/my-project"
```

### Integration with Git

Add to your project's `.gitignore`:
```
# Mnemosyne local storage
.mnemosyne/
```

Consider team memory sharing:
```bash
# Export memories for sharing
python -c "
from mnemosyne import MemoryStorage, load_config
storage = MemoryStorage(load_config())
# Export logic here
"
```

## Next Steps

1. **Start using**: Open Cursor, start a chat, try the tools
2. **Build habits**: Store decisions as you make them
3. **Explore relationships**: Use graph tools to discover patterns
4. **Team adoption**: Share configuration with your team
5. **Customize**: Adjust settings for your workflow

🚀 **You're ready to never lose context again!**