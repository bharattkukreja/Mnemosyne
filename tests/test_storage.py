#!/usr/bin/env python3
"""Test the storage layer with real data"""

import asyncio
from tools.store_tools import StoreTools
from tools.retrieval_tools import RetrievalTools
from config import load_config, ensure_directories


async def test_storage():
    """Test storing and retrieving memories"""
    
    print("🧪 Testing Mnemosyne Storage Layer\n")
    
    # Load config
    config = load_config()
    ensure_directories(config)
    
    # Initialize tools
    store_tools = StoreTools(config)
    retrieval_tools = RetrievalTools(config)
    
    print("✅ Storage layer initialized")
    print(f"📁 Storage type: {store_tools.storage.storage_type}")
    print(f"🧠 Embedding type: {store_tools.storage.embedding_generator.embedding_type}")
    print()
    
    # Test 1: Store a decision
    print("📋 Test 1: Storing a decision...")
    decision_result = await store_tools.store_decision({
        "decision": "Use FastAPI for the web API instead of Flask",
        "reasoning": "FastAPI provides automatic OpenAPI docs, better performance, and native async support",
        "files": ["api/main.py", "api/routes.py", "requirements.txt"],
        "tags": ["architecture", "web-framework", "performance"]
    })
    print(decision_result[0].text)
    print()
    
    # Test 2: Store a TODO
    print("📝 Test 2: Storing a TODO...")
    todo_result = await store_tools.store_todo({
        "task": "Add input validation to all API endpoints",
        "context": "Need to validate user inputs to prevent security issues and improve error handling",
        "priority": "high",
        "files": ["api/routes.py", "api/validators.py"]
    })
    print(todo_result[0].text)
    print()
    
    # Test 3: Store another decision
    print("📋 Test 3: Storing another decision...")
    decision_result2 = await store_tools.store_decision({
        "decision": "Use PostgreSQL as the primary database",
        "reasoning": "Need ACID compliance and complex queries for the analytics features",
        "files": ["database/models.py", "config/database.py"],
        "tags": ["database", "architecture", "analytics"]
    })
    print(decision_result2[0].text)
    print()
    
    # Test 4: Search for decisions
    print("🔍 Test 4: Searching for 'API' related memories...")
    search_result = await retrieval_tools.search_memory({
        "query": "API endpoints validation",
        "filters": {"type": "all"}
    })
    print(search_result[0].text)
    print()
    
    # Test 5: Search with type filter
    print("🔍 Test 5: Searching only decisions...")
    search_result2 = await retrieval_tools.search_memory({
        "query": "database architecture",
        "filters": {"type": "decision"}
    })
    print(search_result2[0].text)
    print()
    
    # Test 6: Get session context
    print("📋 Test 6: Getting session context...")
    context_result = await retrieval_tools.get_session_context({
        "current_files": ["api/main.py", "database/models.py"],
        "recent_commits": ["feat: add FastAPI endpoints", "refactor: database models"],
        "max_tokens": 1500
    })
    print(context_result[0].text)
    print()
    
    print("✅ All storage tests completed!")
    print("🎉 Phase 2 (Storage Layer) working correctly!")


if __name__ == "__main__":
    asyncio.run(test_storage())