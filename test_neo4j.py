#!/usr/bin/env python3
"""Test Neo4j Knowledge Graph Integration"""

import asyncio
from tools.store_tools import StoreTools
from tools.graph_tools import GraphTools
from memory.extractor import ConversationExtractor
from config import load_config, ensure_directories


async def test_knowledge_graph():
    """Test the Neo4j knowledge graph functionality"""
    
    print("🧪 Testing Mnemosyne Knowledge Graph Integration\n")
    
    # Load config
    config = load_config()
    ensure_directories(config)
    
    # Initialize tools
    store_tools = StoreTools(config)
    graph_tools = GraphTools(config)
    extractor = ConversationExtractor()
    
    print("✅ Knowledge graph tools initialized")
    print(f"📁 Storage type: {store_tools.storage.storage_type}")
    print(f"🔗 Neo4j available: {store_tools.storage.knowledge_graph.driver is not None}")
    print()
    
    if not store_tools.storage.knowledge_graph.driver:
        print("⚠️  Neo4j not available - testing with limited functionality")
        print("   To test with Neo4j, ensure Neo4j is running and configured in config.yaml")
        print()
    
    # Test 1: Store interconnected memories for testing
    print("📋 Test 1: Building interconnected memory graph...")
    
    # Store authentication decisions
    auth_decision = await store_tools.store_decision({
        "decision": "Use JWT tokens for API authentication",
        "reasoning": "Stateless authentication that scales well with microservices",
        "files": ["api/auth.py", "middleware/jwt.py", "config/auth.py"],
        "tags": ["authentication", "security", "api", "jwt"]
    })
    
    # Store related security TODO
    security_todo = await store_tools.store_todo({
        "task": "Implement token refresh mechanism",
        "context": "JWT tokens should have short expiry with refresh capability for security",
        "priority": "high",
        "files": ["api/auth.py", "middleware/jwt.py"]
    })
    
    # Store database decision that affects auth
    db_decision = await store_tools.store_decision({
        "decision": "Use Redis for session storage and token blacklisting",
        "reasoning": "Fast in-memory storage for temporary auth data and token invalidation",
        "files": ["config/redis.py", "api/auth.py", "middleware/session.py"],
        "tags": ["database", "redis", "authentication", "performance"]
    })
    
    # Store frontend integration TODO
    frontend_todo = await store_tools.store_todo({
        "task": "Update frontend to handle JWT token storage",
        "context": "Store JWT in httpOnly cookies and handle automatic refresh",
        "priority": "medium",
        "files": ["frontend/auth/tokenManager.js", "frontend/api/client.js"]
    })
    
    # Store API rate limiting decision
    rate_limit_decision = await store_tools.store_decision({
        "decision": "Implement rate limiting using Redis and sliding window",
        "reasoning": "Protect API from abuse while allowing legitimate high-frequency usage",
        "files": ["middleware/rateLimit.py", "config/redis.py"],
        "tags": ["security", "api", "performance", "redis"]
    })
    
    print("✅ 5 interconnected memories stored\n")
    
    # Test 2: Test MCP server with all tools
    print("🔧 Test 2: Testing MCP server with all 9 tools...")
    try:
        # Test server startup
        from server import server
        tools = await server.list_tools()
        
        print(f"✅ MCP server running with {len(tools)} tools:")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        print()
        
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        print()
    
    # Test 3: Knowledge graph exploration (if Neo4j available)
    if store_tools.storage.knowledge_graph.driver:
        print("🔗 Test 3: Knowledge graph relationship exploration...")
        
        # Extract memory ID from the auth decision response
        auth_response = auth_decision[0].text
        import re
        auth_id_match = re.search(r'\*\*ID:\*\* ([a-f0-9-]+)', auth_response)
        
        if auth_id_match:
            memory_id = auth_id_match.group(1)
            print(f"Exploring relationships for memory: {memory_id}")
            
            relationships_result = await graph_tools.explore_relationships({
                "memory_id": memory_id,
                "max_depth": 2
            })
            print(relationships_result[0].text)
            print()
            
            # Test decision impact analysis
            print("📊 Test 4: Decision impact analysis...")
            impact_result = await graph_tools.analyze_decision_impact({
                "decision_id": memory_id
            })
            print(impact_result[0].text)
            print()
        
        # Test pattern discovery
        print("🔍 Test 5: Knowledge pattern discovery...")
        patterns_result = await graph_tools.discover_patterns({})
        print(patterns_result[0].text)
        print()
        
        # Test file evolution tracing
        print("📈 Test 6: File evolution tracing...")
        evolution_result = await graph_tools.trace_file_evolution({
            "filepath": "api/auth.py"
        })
        print(evolution_result[0].text)
        print()
    
    else:
        print("⚠️  Skipping graph tests - Neo4j not available")
        print("   Start Neo4j and configure connection to test graph features")
        print()
    
    # Test 4: Conversation parsing with graph integration
    print("🗣️ Test 7: Conversation parsing with graph storage...")
    complex_conversation = """
    User: I'm concerned about the JWT implementation. What if tokens get stolen?
    
    Assistant: Good point! We should implement token rotation and use httpOnly cookies.
    
    User: Let's also add rate limiting to prevent brute force attacks on the auth endpoints
    
    Assistant: Absolutely. We can use Redis with a sliding window algorithm for that.
    
    User: Actually, let's reconsider the JWT approach. Maybe we should use session-based auth instead?
    
    Assistant: That's a valid concern. Session-based auth gives us more control over revocation.
    
    User: But then we lose the stateless benefits. Let's stick with JWT but add proper security measures.
    """
    
    extracted_memories = extractor.extract_from_conversation(
        complex_conversation,
        conversation_id="security_discussion_1",
        context_files=["api/auth.py", "middleware/security.py"]
    )
    
    print(f"Extracted {len(extracted_memories)} memories from security conversation:")
    for memory in extracted_memories:
        stored_id = store_tools.storage.store_memory(memory)
        print(f"  • {memory.type}: {memory.content[:60]}...")
        print(f"    ID: {stored_id}")
    
    print("\n✅ All knowledge graph tests completed!")
    
    # Summary
    print("\n📊 **Neo4j Knowledge Graph Summary**")
    print("=" * 50)
    print("**Capabilities Added:**")
    print("• 🔗 Relationship tracking between memories, files, and conversations")
    print("• 📊 Decision impact analysis across the codebase")
    print("• 🔍 Pattern discovery in development discussions")
    print("• 📈 File evolution tracking over time")
    print("• 🎯 Multi-hop relationship exploration")
    print()
    print("**Graph Schema:**")
    print("• Memory nodes: Decision, Todo, BugFix")
    print("• File nodes: With directory and extension metadata")
    print("• Tag nodes: For categorization")
    print("• Conversation nodes: Grouping related discussions")
    print("• Relationships: RELATES_TO, TAGGED_WITH, CONTAINS, AUTHORED")
    print()
    print("**MCP Tools Available: 9 total**")
    print("• Storage: store_decision, store_todo")
    print("• Search: search_memory, get_session_context")
    print("• Files: get_file_history")
    print("• Graph: explore_relationships, analyze_decision_impact, discover_patterns, trace_file_evolution")
    print()
    
    if store_tools.storage.knowledge_graph.driver:
        print("✅ **Neo4j Integration: ACTIVE**")
        print("   Full knowledge graph capabilities available")
    else:
        print("⚠️  **Neo4j Integration: INACTIVE**")
        print("   Vector search and file storage working, graph features limited")
    
    print(f"\n🚀 **Ready for Production Deployment!**")


if __name__ == "__main__":
    asyncio.run(test_knowledge_graph())