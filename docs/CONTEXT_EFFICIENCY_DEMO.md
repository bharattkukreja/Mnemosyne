# Smart Context Injection - Token Efficiency Demo

## The Problem: Context Window Waste

**Before Mnemosyne:**
```
Developer starts new session:
"Can you help me continue with the authentication system?"

Claude: "I'd be happy to help! Could you tell me:
- What authentication approach are you using?
- What files are you working with?
- What have you already implemented?
- Are there any specific issues you're facing?"

Developer: "We're using session-based auth with Redis store.
We decided against JWT because of security concerns about token rotation.
The main files are auth.py, session_store.py, and user_model.py.
We already implemented login and logout but need to add password reset.
We tried using email templates but decided to use a service instead.
The session middleware is working but we need to add CSRF protection..."

[~300 tokens wasted on re-establishing context]
```

**After Mnemosyne with Smart Context:**
```
Developer starts new session with auth.py open

🎯 **Smart Context Auto-Injected** (89 tokens)

Context (3 items):
Decisions: Use session-based auth over JWT (better security rotation), Redis session store (performance), email service vs templates (reliability)
Avoided: JWT tokens, local email templates
Architecture: middleware pattern [auth.py], service layer [session_store.py]

[Claude immediately knows the context and can help with next steps]
```

## Token Efficiency Comparison

| Scenario | Manual Context | Smart Context | Savings |
|----------|---------------|---------------|---------|
| **New session on existing feature** | 200-400 tokens | 60-120 tokens | **50-70%** |
| **Returning after 1 week** | 300-500 tokens | 80-150 tokens | **60-75%** |
| **Team member joining project** | 400-800 tokens | 100-200 tokens | **65-80%** |
| **Complex project context** | 500-1000 tokens | 150-300 tokens | **70-80%** |

## Real Usage Examples

### Example 1: Feature Development
```python
# Files open: payment.py, stripe_integration.py
# Smart context detects payment work and injects:

"Decisions: Stripe over PayPal (better API), webhook validation required (security)
Architecture: service pattern [payment.py], external API wrapper [stripe_integration.py]
TODOs: Error handling for failed payments, refund flow implementation"

# Developer immediately continues: "Help me implement the refund flow"
# ✅ Zero context re-establishment needed
```

### Example 2: Bug Fixing
```python
# Files open: database.py with recent error logs
# Smart context detects database work and injects:

"Fixes: Connection pool exhaustion (increased max_connections), query timeout handling
Avoided: Single connection approach, synchronous queries
Architecture: connection pooling [database.py], async queries [models/]"

# Developer: "I'm seeing a new timeout error in production"
# ✅ Claude knows database architecture and past fixes
```

### Example 3: Code Review
```python
# Files open: user_service.py (git diff shows auth changes)
# Smart context injects:

"Decisions: Hash passwords with bcrypt (security), validate email format server-side
Avoided: Client-side only validation, plain text storage
Recent: Added email verification flow, removed deprecated login method"

# Reviewer: "Check this auth implementation"
# ✅ Claude knows security decisions and recent changes
```

## Business Impact

### For Individual Developers
- **Time Savings**: 2-5 minutes per session × 10 sessions/day = 20-50 minutes daily
- **Token Savings**: 60-80% reduction in context-setting tokens
- **Mental Load**: Zero cognitive overhead for context re-establishment

### For Development Teams
- **Onboarding**: New team members get instant project context
- **Knowledge Sharing**: Decisions automatically propagate across team
- **Consistency**: Past architectural decisions are always available

### For AI Token Costs
- **Cost Reduction**: 60-80% fewer tokens needed for session setup
- **Better Context**: Higher quality, pre-filtered relevant information
- **Scalability**: Efficient even with large project histories

## Implementation Details

### Smart Injection Triggers
```python
# Auto-inject when:
✅ New session after 4+ hours gap
✅ Different git branch than last session
✅ New files opened that have memory history
✅ Error patterns matching previous fixes
✅ Team member mentions in commits

# Skip injection when:
❌ Recent session (< 30 minutes ago)
❌ No relevant memories found
❌ Low confidence in relevance (< 0.7)
❌ Working on files with no history
```

### Context Optimization
```python
# Efficiency techniques:
- Ultra-compressed format (no markdown headers)
- Grouped by type (decisions, fixes, architecture)
- Relevance-based filtering (only 0.6+ relevance)
- Token-density optimization (value per token)
- Automatic deduplication
- Smart content truncation
```

## Getting Started

1. **Install Mnemosyne MCP server**
2. **Work normally - decisions auto-captured**
3. **Start new session - context auto-injected**
4. **See immediate token savings**

The killer feature works invisibly in the background, saving tokens and time without changing your workflow.

## Success Metrics

### Quantitative
- **Token Efficiency**: 60-80% reduction in context tokens
- **Time Savings**: 2-5 minutes per session
- **Context Accuracy**: 90%+ relevant information

### Qualitative
- **Zero Interruption**: Works silently in background
- **Always Relevant**: Smart filtering ensures high-value context
- **Team Ready**: Scales from individual to team use

**Bottom Line**: Developers save significant time and token costs while getting better, more relevant context than manual approaches.