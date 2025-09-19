# Smart Context Improvements - Implementation Plan

## Problem Statement

Current smart context system has critical gaps that prevent effective context preservation between Claude sessions:

1. **Session Detection is Incomplete** - Can't detect when new sessions start or track previous activity
2. **No Persistent Session State** - Each invocation starts fresh, losing continuity
3. **Limited Context Compression** - Focuses on token counting vs semantic importance
4. **No Conversation Summarization** - Stores individual memories but no session summaries
5. **Weak Confidence Thresholds** - Often returns "no context needed" when context is valuable

## Solution Architecture

### 1. Persistent Session Tracking

**Goal**: Track session boundaries and maintain state between Claude invocations

**Components**:
- `SessionDatabase` - SQLite database for session metadata storage
- `SessionTracker` - Detects session boundaries using multiple signals
- `SessionContext` - Enhanced with persistent state

**Implementation**:
```python
# context/session_tracker.py
class SessionTracker:
    - detect_session_boundary() -> SessionBoundary
    - track_file_activity() -> FileActivity
    - get_session_continuity_score() -> float
    - store_session_metadata() -> SessionMetadata

# Database schema
Sessions:
  - id, start_time, end_time, branch, working_dir
  - active_files, file_access_patterns, git_commits
  - context_summary, token_usage, continuity_score
```

**Detection Signals**:
- Time gaps > 30min = new session
- Git branch changes = new session
- File access pattern changes = potential new session
- Working directory changes = new session

### 2. Progressive Context Summarization

**Goal**: Create hierarchical context summaries for efficient retrieval

**Hierarchy**:
- **Immediate** (last 2 hours): Full detail, recent decisions/changes
- **Recent** (last 24 hours): Summarized work, key decisions
- **Historical** (last week): High-level progress, major decisions only

**Components**:
```python
# context/summarizer.py
class ContextSummarizer:
    - summarize_session() -> SessionSummary
    - build_context_thread() -> ContextThread
    - compress_historical_context() -> CompressedContext
    - detect_semantic_duplicates() -> List[DuplicateGroup]

# Context Threads - link related work across sessions
ContextThread:
  - theme: str (e.g., "authentication system")
  - sessions: List[SessionSummary]
  - key_decisions: List[Decision]
  - current_status: str
```

**Summarization Strategy**:
- Real-time: Summarize completed sessions immediately
- Progressive: Compress older summaries to save tokens
- Semantic: Group related work across time boundaries

### 3. Smart Context Triggers

**Goal**: More intelligent decisions about when and what context to inject

**Enhanced Triggers**:
- **File Continuity**: Auto-inject when returning to recently modified files
- **Branch Context**: Full context injection on branch switches
- **Time-Based**: Progressive injection based on gap duration
- **Work Pattern**: Adapt to developer's typical session patterns

**Confidence Scoring**:
```python
# New confidence calculation
def calculate_injection_confidence(session_context):
    base_score = 0.0

    # File continuity (high value)
    if recent_files_overlap > 0.7: base_score += 0.4

    # Time gap appropriateness
    if 30min < time_gap < 4hours: base_score += 0.3

    # Work context richness
    if available_context_value > threshold: base_score += 0.2

    # Branch/project continuity
    if same_branch and same_project: base_score += 0.1

    return min(base_score, 1.0)
```

**Adaptive Thresholds**:
- Lower thresholds for developers who work in short bursts
- Higher thresholds for long-session developers
- Project-specific thresholds based on complexity

### 4. Token-Efficient Context Compression

**Goal**: Maximize context value per token used

**Compression Strategies**:

**Immediate Context** (0-2 hours):
```
Recent work on user authentication:
- ✅ Implemented JWT middleware in auth/middleware.py
- ⚠️ Rejected bcrypt (too slow) → using argon2
- 🔄 TODO: Add refresh token logic
- 📁 Modified: auth/middleware.py, models/user.py
```

**Recent Context** (2-24 hours):
```
Yesterday: Completed user auth system (JWT + argon2), rejected bcrypt approach.
Key decisions: middleware pattern, refresh tokens pending.
Files: auth/, models/user.py
```

**Historical Context** (>24 hours):
```
Last week: Auth system (JWT), user management, API structure.
```

**Smart Deduplication**:
- Detect repeated context across time periods
- Merge similar decisions and outcomes
- Preserve only evolving/conflicting information

### 5. Implementation Phases

#### Phase 1: Session Tracking Foundation
- [ ] Create `SessionDatabase` with SQLite backend
- [ ] Implement `SessionTracker` with basic boundary detection
- [ ] Add session metadata persistence
- [ ] Test session continuity detection

#### Phase 2: Context Summarization
- [ ] Build `ContextSummarizer` with hierarchical levels
- [ ] Implement session summary generation
- [ ] Add context thread linking logic
- [ ] Create semantic deduplication

#### Phase 3: Smart Triggers Enhancement
- [ ] Improve confidence scoring with new factors
- [ ] Add adaptive threshold logic
- [ ] Implement file continuity tracking
- [ ] Add work pattern analysis

#### Phase 4: Compression Optimization
- [ ] Design token-efficient formats
- [ ] Implement progressive compression
- [ ] Add semantic importance scoring
- [ ] Optimize context selection algorithm

#### Phase 5: Integration & Testing
- [ ] Integrate all components with existing smart_injector
- [ ] Add comprehensive logging and metrics
- [ ] Test with real coding sessions
- [ ] Optimize performance and memory usage

## Success Metrics

**Token Efficiency**:
- 50% reduction in manual context re-establishment
- 80% of sessions start with relevant auto-injected context
- Average context injection under 500 tokens with high value

**Context Quality**:
- 90% of auto-injected context rated as relevant by developers
- Context continuity maintained across 95% of session boundaries
- Zero context loss for work sessions under 4 hours apart

**Developer Experience**:
- Sub-100ms context injection latency
- No manual "remind me what I was working on" queries needed
- Seamless session transitions with preserved work context

## Technical Implementation Notes

**Database Schema**:
```sql
-- Session tracking
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    branch TEXT,
    working_dir TEXT,
    active_files JSON,
    git_commits JSON,
    context_summary TEXT,
    continuity_score REAL
);

-- Session context summaries
CREATE TABLE session_summaries (
    session_id TEXT,
    level TEXT, -- immediate/recent/historical
    summary_text TEXT,
    token_count INTEGER,
    created_at TIMESTAMP
);

-- Context threads
CREATE TABLE context_threads (
    id TEXT PRIMARY KEY,
    theme TEXT,
    sessions JSON,
    key_decisions JSON,
    current_status TEXT
);
```

**Configuration**:
```yaml
smart_context:
  session_tracking:
    boundary_time_threshold: 1800  # 30 minutes
    file_continuity_threshold: 0.7
    max_session_duration: 14400   # 4 hours

  summarization:
    immediate_window: 7200    # 2 hours
    recent_window: 86400      # 24 hours
    compression_ratio: 0.3    # compress to 30% of original

  injection:
    base_confidence: 0.3
    max_tokens: 500
    adaptive_thresholds: true
```

This plan transforms the smart context system from a basic memory retrieval tool into an intelligent session continuity system that preserves and optimally delivers context across all Claude interactions.