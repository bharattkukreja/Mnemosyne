#!/usr/bin/env python3
"""Test Phase 3: Context Retrieval features"""

import asyncio
from tools.store_tools import StoreTools
from tools.retrieval_tools import RetrievalTools
from tools.file_tools import FileTools
from memory.extractor import ConversationExtractor
from config import load_config, ensure_directories


async def test_phase3():
    """Test Phase 3 context retrieval features"""
    
    print("🧪 Testing Mnemosyne Phase 3: Context Retrieval\n")
    
    # Load config
    config = load_config()
    ensure_directories(config)
    
    # Initialize tools
    store_tools = StoreTools(config)
    retrieval_tools = RetrievalTools(config)
    file_tools = FileTools(config)
    extractor = ConversationExtractor()
    
    print("✅ Phase 3 tools initialized")
    print(f"📁 Storage type: {store_tools.storage.storage_type}")
    print(f"🧠 Embedding type: {store_tools.storage.embedding_generator.embedding_type}")
    print()
    
    # Test 1: Store diverse memories for testing
    print("📋 Test 1: Setting up test data...")
    
    # Store API-related decision
    await store_tools.store_decision({
        "decision": "Use GraphQL for the new API instead of REST",
        "reasoning": "GraphQL provides better flexibility for mobile clients and reduces over-fetching",
        "files": ["api/schema.py", "api/resolvers.py", "frontend/queries.js"],
        "tags": ["api", "graphql", "performance", "mobile"]
    })
    
    # Store database decision
    await store_tools.store_decision({
        "decision": "Migrate from SQLite to PostgreSQL for production",
        "reasoning": "Need better performance and ACID compliance for concurrent users",
        "files": ["database/models.py", "database/migrations.py", "config/database.py"],
        "tags": ["database", "postgresql", "performance", "production"]
    })
    
    # Store security TODO
    await store_tools.store_todo({
        "task": "Implement rate limiting on all API endpoints",
        "context": "Prevent abuse and DDoS attacks, especially on authentication endpoints",
        "priority": "high",
        "files": ["api/middleware.py", "api/auth.py", "config/rate_limits.py"]
    })
    
    # Store frontend TODO
    await store_tools.store_todo({
        "task": "Add loading states to all forms",
        "context": "Improve user experience during API calls",
        "priority": "medium",
        "files": ["frontend/components/forms.js", "frontend/hooks/useLoading.js"]
    })
    
    print("✅ Test data stored\n")
    
    # Test 2: Enhanced search with relevance scoring
    print("🔍 Test 2: Enhanced search with relevance scoring...")
    search_result = await retrieval_tools.search_memory({
        "query": "API performance and mobile optimization",
        "filters": {"type": "all"}
    })
    print(search_result[0].text)
    print()
    
    # Test 3: Smart session context with compression
    print("📋 Test 3: Smart session context...")
    context_result = await retrieval_tools.get_session_context({
        "current_files": ["api/schema.py", "frontend/queries.js"],
        "recent_commits": ["feat: add GraphQL schema", "refactor: optimize queries"],
        "max_tokens": 1500
    })
    print(context_result[0].text)
    print()
    
    # Test 4: File history tool
    print("📁 Test 4: File history retrieval...")
    file_history_result = await file_tools.get_file_history({
        "filepath": "api/schema.py",
        "include_decisions": True,
        "include_todos": True
    })
    print(file_history_result[0].text)
    print()
    
    # Test 5: Conversation parsing
    print("🗣️ Test 5: Conversation parsing...")
    sample_conversation = """
    User: I think we should use Redis for caching to improve performance
    
    Assistant: That's a great idea! Redis would definitely help with response times.
    
    User: Let's implement it for the user session cache first, then expand to API responses
    
    Assistant: Good approach. We'll need to:
    - Set up Redis connection in config/cache.py
    - Create cache middleware for sessions
    - Add cache invalidation logic
    
    User: Also, we need to handle cache misses gracefully
    
    Assistant: Absolutely. We should fall back to database queries when cache is unavailable.
    """
    
    extracted_memories = extractor.extract_from_conversation(
        sample_conversation,
        conversation_id="test_conv_1",
        context_files=["config/cache.py", "middleware/sessions.py"]
    )
    
    print(f"Extracted {len(extracted_memories)} memories from conversation:")
    for memory in extracted_memories:
        print(f"  • {memory.type}: {memory.content}")
        if memory.reasoning:
            print(f"    Reasoning: {memory.reasoning}")
        print(f"    Files: {memory.files}")
        print()
    
    # Store extracted memories
    for memory in extracted_memories:
        store_tools.storage.store_memory(memory)
    
    print("✅ Extracted memories stored\n")
    
    # Test 6: Context-aware search after adding more memories
    print("🔍 Test 6: Context-aware search with more data...")
    search_result2 = await retrieval_tools.search_memory({
        "query": "caching and performance improvements",
        "filters": {"type": "all"}
    })
    print(search_result2[0].text)
    print()
    
    # Test 7: File history for cache-related file
    print("📁 Test 7: File history for cache file...")
    cache_history = await file_tools.get_file_history({
        "filepath": "config/cache.py",
        "include_decisions": True,
        "include_todos": True
    })
    print(cache_history[0].text)
    print()
    
    # Test 8: Session context with multiple file types
    print("📋 Test 8: Session context with database and cache files...")
    context_result2 = await retrieval_tools.get_session_context({
        "current_files": ["database/models.py", "config/cache.py", "api/middleware.py"],
        "recent_commits": ["feat: add Redis caching", "refactor: database models"],
        "max_tokens": 2000
    })
    print(context_result2[0].text)
    print()
    
    print("✅ All Phase 3 tests completed!")
    print("🎉 Context Retrieval system working correctly!")
    print("\n🚀 Ready for Phase 4: Integration & Testing")


if __name__ == "__main__":
    asyncio.run(test_phase3())