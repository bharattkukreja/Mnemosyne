#!/usr/bin/env python3
"""
Mnemosyne Database Explorer
Interactive tool to visualize and explore ChromaDB and Neo4j data
"""

import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from tabulate import tabulate
import textwrap

from memory.storage import MemoryStorage
from memory.graph import KnowledgeGraph
from config import load_config


class DatabaseExplorer:
    """Interactive database explorer for Mnemosyne"""

    def __init__(self):
        self.config = load_config()
        self.storage = MemoryStorage(self.config)
        self.graph = KnowledgeGraph(self.config)

    def run(self):
        """Main interactive loop"""
        print("🧠 Mnemosyne Database Explorer")
        print("=" * 50)

        while True:
            self.show_menu()
            choice = input("\nEnter your choice (1-8, q to quit): ").strip().lower()

            if choice in ['q', 'quit', 'exit']:
                print("👋 Goodbye!")
                break

            try:
                if choice == '1':
                    self.show_overview()
                elif choice == '2':
                    self.explore_chromadb()
                elif choice == '3':
                    self.explore_neo4j()
                elif choice == '4':
                    self.search_memories()
                elif choice == '5':
                    self.show_relationships()
                elif choice == '6':
                    self.analyze_patterns()
                elif choice == '7':
                    self.export_data()
                elif choice == '8':
                    self.show_neo4j_queries()
                else:
                    print("❌ Invalid choice. Please try again.")

            except Exception as e:
                print(f"❌ Error: {e}")

            input("\nPress Enter to continue...")

    def show_menu(self):
        """Display main menu"""
        print("\n📋 What would you like to explore?")
        print("1. 📊 Database Overview")
        print("2. 🗃️  ChromaDB Data (Vector Storage)")
        print("3. 🕸️  Neo4j Data (Knowledge Graph)")
        print("4. 🔍 Search Memories")
        print("5. 🔗 View Relationships")
        print("6. 📈 Analyze Patterns")
        print("7. 💾 Export Data")
        print("8. 🎯 Neo4j Browser Queries")
        print("q. ❌ Quit")

    def show_overview(self):
        """Show overview of both databases"""
        print("\n📊 MNEMOSYNE DATABASE OVERVIEW")
        print("=" * 60)

        # ChromaDB stats
        if self.storage.storage_type == 'chromadb':
            results = self.storage.collection.get()
            chroma_count = len(results['ids'])
            collection_name = self.storage.collection.name
            print(f"🗃️  ChromaDB: {chroma_count} memories in '{collection_name}' collection")
            print(f"📍 Location: {self.config.storage.vector_db_path}")
        else:
            print("🗃️  ChromaDB: Not available (using file storage)")

        # Neo4j stats
        if self.graph.driver:
            with self.graph.driver.session() as session:
                result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
                print(f"\n🕸️  Neo4j Graph Database:")
                for record in result:
                    print(f"   {record['type']}: {record['count']} nodes")

                result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count")
                print(f"   Relationships:")
                for record in result:
                    print(f"   {record['rel_type']}: {record['count']}")
        else:
            print("🕸️  Neo4j: Not available")

    def explore_chromadb(self):
        """Explore ChromaDB data in detail"""
        print("\n🗃️  CHROMADB VECTOR STORAGE")
        print("=" * 60)

        if self.storage.storage_type != 'chromadb':
            print("❌ ChromaDB not available")
            return

        results = self.storage.collection.get(include=['metadatas', 'documents', 'embeddings'])

        if not results['ids']:
            print("📭 No memories stored yet")
            return

        print(f"📊 Found {len(results['ids'])} memories")
        print("\nChoose view:")
        print("1. Summary table")
        print("2. Detailed view")
        print("3. Search by content")

        choice = input("Enter choice (1-3): ").strip()

        if choice == '1':
            self._show_chromadb_table(results)
        elif choice == '2':
            self._show_chromadb_detailed(results)
        elif choice == '3':
            self._search_chromadb()

    def _show_chromadb_table(self, results):
        """Show ChromaDB data as a table"""
        table_data = []

        for i, (id, doc, meta) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
            files = json.loads(meta.get('files', '[]'))
            tags = json.loads(meta.get('tags', '[]'))

            table_data.append([
                i + 1,
                id[:8] + "...",
                meta.get('type', 'unknown'),
                textwrap.shorten(doc, width=40),
                ', '.join(files[:2]) + ('...' if len(files) > 2 else ''),
                ', '.join(tags[:3]) + ('...' if len(tags) > 3 else ''),
                meta.get('timestamp', 'unknown')[:10]
            ])

        headers = ['#', 'ID', 'Type', 'Content', 'Files', 'Tags', 'Date']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))

    def _show_chromadb_detailed(self, results):
        """Show detailed ChromaDB data"""
        for i, (id, doc, meta) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
            files = json.loads(meta.get('files', '[]'))
            tags = json.loads(meta.get('tags', '[]'))

            print(f"\n📄 Memory {i+1}/{len(results['ids'])}")
            print(f"🆔 ID: {id}")
            print(f"📝 Content: {doc}")
            print(f"🏷️  Type: {meta.get('type', 'unknown')}")
            print(f"📁 Files: {files}")
            print(f"🏷️  Tags: {tags}")
            print(f"⏰ Time: {meta.get('timestamp', 'unknown')}")
            print(f"🧮 Embedding: {len(results['embeddings'][i])} dimensions")
            print("-" * 60)

            if i < len(results['ids']) - 1:
                cont = input("Continue? (y/n): ").strip().lower()
                if cont != 'y':
                    break

    def _search_chromadb(self):
        """Search ChromaDB by content"""
        query = input("Enter search query: ").strip()
        if not query:
            return

        # Use the storage's search functionality
        embedding = self.storage.embedding_generator.generate_embedding(query)
        results = self.storage.collection.query(
            query_embeddings=[embedding],
            n_results=5,
            include=['metadatas', 'documents', 'distances']
        )

        print(f"\n🔍 Search results for: '{query}'")
        print("-" * 60)

        for i, (id, doc, meta, dist) in enumerate(zip(
            results['ids'][0], results['documents'][0],
            results['metadatas'][0], results['distances'][0]
        )):
            print(f"\n{i+1}. Similarity: {1-dist:.3f}")
            print(f"   Content: {doc}")
            print(f"   Type: {meta.get('type', 'unknown')}")
            print(f"   Files: {json.loads(meta.get('files', '[]'))}")

    def explore_neo4j(self):
        """Explore Neo4j graph data"""
        print("\n🕸️  NEO4J KNOWLEDGE GRAPH")
        print("=" * 60)

        if not self.graph.driver:
            print("❌ Neo4j not available")
            return

        print("Choose exploration:")
        print("1. Show all nodes and relationships")
        print("2. Explore specific memory")
        print("3. Show file relationships")
        print("4. Show tag connections")
        print("5. Custom Cypher query")

        choice = input("Enter choice (1-5): ").strip()

        if choice == '1':
            self._show_neo4j_overview()
        elif choice == '2':
            self._explore_specific_memory()
        elif choice == '3':
            self._show_file_relationships()
        elif choice == '4':
            self._show_tag_connections()
        elif choice == '5':
            self._custom_cypher_query()

    def _show_neo4j_overview(self):
        """Show Neo4j overview"""
        with self.graph.driver.session() as session:
            print("\n📊 All Nodes:")
            result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC")
            for record in result:
                print(f"   {record['type']}: {record['count']}")

            print("\n🔗 All Relationships:")
            result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count ORDER BY count DESC")
            for record in result:
                print(f"   {record['rel_type']}: {record['count']}")

            print("\n📄 Recent Memories:")
            result = session.run("""
                MATCH (m:Memory)
                RETURN m.id as id, m.content as content, m.type as type
                ORDER BY m.timestamp DESC
                LIMIT 5
            """)

            for i, record in enumerate(result, 1):
                print(f"   {i}. [{record['type']}] {record['content'][:50]}...")
                print(f"      ID: {record['id'][:8]}...")

    def _explore_specific_memory(self):
        """Explore a specific memory's relationships"""
        with self.graph.driver.session() as session:
            # Show available memories
            result = session.run("MATCH (m:Memory) RETURN m.id as id, m.content as content ORDER BY m.timestamp DESC")
            memories = list(result)

            if not memories:
                print("No memories found")
                return

            print("\nAvailable memories:")
            for i, record in enumerate(memories, 1):
                print(f"{i}. {record['content'][:60]}...")

            try:
                choice = int(input(f"Choose memory (1-{len(memories)}): "))
                if 1 <= choice <= len(memories):
                    memory_id = memories[choice-1]['id']
                    self._show_memory_relationships(memory_id)
            except ValueError:
                print("Invalid choice")

    def _show_memory_relationships(self, memory_id: str):
        """Show relationships for a specific memory"""
        with self.graph.driver.session() as session:
            result = session.run("""
                MATCH (m:Memory {id: $memory_id})-[r]->(target)
                RETURN type(r) as relationship, labels(target)[0] as target_type,
                       coalesce(target.path, target.name, target.id) as target_name
                ORDER BY relationship, target_type
            """, memory_id=memory_id)

            print(f"\n🔗 Relationships for memory {memory_id[:8]}...")
            for record in result:
                print(f"   --{record['relationship']}--> {record['target_type']}: {record['target_name']}")

    def _show_file_relationships(self):
        """Show file-based relationships"""
        with self.graph.driver.session() as session:
            result = session.run("""
                MATCH (f:File)<-[:RELATES_TO]-(m:Memory)
                RETURN f.path as file_path, count(m) as memory_count
                ORDER BY memory_count DESC
            """)

            print("\n📁 Files by memory count:")
            for record in result:
                print(f"   {record['file_path']}: {record['memory_count']} memories")

    def _show_tag_connections(self):
        """Show tag-based connections"""
        with self.graph.driver.session() as session:
            result = session.run("""
                MATCH (t:Tag)<-[:TAGGED_WITH]-(m:Memory)
                RETURN t.name as tag_name, count(m) as memory_count
                ORDER BY memory_count DESC
            """)

            print("\n🏷️  Tags by usage:")
            for record in result:
                print(f"   {record['tag_name']}: {record['memory_count']} memories")

    def _custom_cypher_query(self):
        """Run custom Cypher query"""
        print("\n💡 Enter a Cypher query (or 'help' for examples):")
        query = input("cypher> ").strip()

        if query.lower() == 'help':
            print("\n📚 Example queries:")
            print("MATCH (n) RETURN n LIMIT 10")
            print("MATCH (m:Memory)-[r]->(n) RETURN m.content, type(r), n")
            print("MATCH (f:File)<-[:RELATES_TO]-(m:Memory) RETURN f.path, count(m)")
            return

        if not query:
            return

        try:
            with self.graph.driver.session() as session:
                result = session.run(query)
                print("\n📊 Query Results:")
                for record in result:
                    print(f"   {dict(record)}")
        except Exception as e:
            print(f"❌ Query error: {e}")

    def search_memories(self):
        """Search memories across both databases"""
        query = input("\nEnter search query: ").strip()
        if not query:
            return

        print(f"\n🔍 Searching for: '{query}'")
        print("=" * 60)

        # ChromaDB semantic search
        if self.storage.storage_type == 'chromadb':
            embedding = self.storage.embedding_generator.generate_embedding(query)
            results = self.storage.collection.query(
                query_embeddings=[embedding],
                n_results=3,
                include=['metadatas', 'documents', 'distances']
            )

            print("🗃️  ChromaDB Semantic Search:")
            for i, (id, doc, meta, dist) in enumerate(zip(
                results['ids'][0], results['documents'][0],
                results['metadatas'][0], results['distances'][0]
            )):
                print(f"   {i+1}. [{1-dist:.3f}] {doc[:60]}...")

        # Neo4j text search
        if self.graph.driver:
            with self.graph.driver.session() as session:
                result = session.run("""
                    MATCH (m:Memory)
                    WHERE toLower(m.content) CONTAINS toLower($query)
                    RETURN m.content as content, m.type as type
                    LIMIT 3
                """, query=query)

                print("\n🕸️  Neo4j Text Search:")
                for i, record in enumerate(result, 1):
                    print(f"   {i}. [{record['type']}] {record['content'][:60]}...")

    def show_relationships(self):
        """Show interesting relationships in the graph"""
        if not self.graph.driver:
            print("❌ Neo4j not available")
            return

        print("\n🔗 KNOWLEDGE GRAPH RELATIONSHIPS")
        print("=" * 60)

        with self.graph.driver.session() as session:
            # Most connected files
            print("📁 Most discussed files:")
            result = session.run("""
                MATCH (f:File)<-[:RELATES_TO]-(m:Memory)
                RETURN f.path as file, count(m) as memories
                ORDER BY memories DESC LIMIT 5
            """)
            for record in result:
                print(f"   {record['file']}: {record['memories']} memories")

            # Popular tags
            print("\n🏷️  Popular tags:")
            result = session.run("""
                MATCH (t:Tag)<-[:TAGGED_WITH]-(m:Memory)
                RETURN t.name as tag, count(m) as usage
                ORDER BY usage DESC LIMIT 5
            """)
            for record in result:
                print(f"   {record['tag']}: {record['usage']} uses")

            # Recent decision chains
            print("\n🔄 Recent decision patterns:")
            result = session.run("""
                MATCH (m1:Memory)-[:RELATED_TO]->(m2:Memory)
                RETURN m1.content as from_decision, m2.content as to_decision
                LIMIT 3
            """)
            for record in result:
                print(f"   {record['from_decision'][:30]}... → {record['to_decision'][:30]}...")

    def analyze_patterns(self):
        """Analyze patterns in the knowledge base"""
        print("\n📈 KNOWLEDGE PATTERNS ANALYSIS")
        print("=" * 60)

        # Use the graph's pattern discovery
        patterns = self.graph.find_knowledge_patterns()

        if patterns.get('most_active_files'):
            print("📁 Most active files:")
            for item in patterns['most_active_files'][:5]:
                print(f"   {item['file']}: {item['memories']} memories")

        if patterns.get('popular_tags'):
            print("\n🏷️  Popular tags:")
            for item in patterns['popular_tags'][:5]:
                print(f"   {item['tag']}: {item['usage']} uses")

        if patterns.get('decision_chains'):
            print("\n🔗 Decision chain analysis:")
            for item in patterns['decision_chains']:
                print(f"   Chain length {item['length']}: {item['count']} instances")

    def export_data(self):
        """Export data to files"""
        print("\n💾 EXPORT DATA")
        print("=" * 60)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export ChromaDB data
        if self.storage.storage_type == 'chromadb':
            results = self.storage.collection.get(include=['metadatas', 'documents'])

            export_data = []
            for id, doc, meta in zip(results['ids'], results['documents'], results['metadatas']):
                export_data.append({
                    'id': id,
                    'content': doc,
                    'metadata': meta
                })

            filename = f"chromadb_export_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"✓ ChromaDB data exported to {filename}")

        # Export Neo4j data
        if self.graph.driver:
            with self.graph.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    OPTIONAL MATCH (n)-[r]->(m)
                    RETURN n, r, m
                """)

                export_data = {
                    'nodes': [],
                    'relationships': []
                }

                for record in result:
                    if record['n']:
                        export_data['nodes'].append(dict(record['n']))
                    if record['r'] and record['m']:
                        export_data['relationships'].append({
                            'from': dict(record['n']),
                            'relationship': type(record['r']).__name__,
                            'to': dict(record['m'])
                        })

                filename = f"neo4j_export_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                print(f"✓ Neo4j data exported to {filename}")

    def show_neo4j_queries(self):
        """Show useful Neo4j browser queries"""
        print("\n🎯 NEO4J BROWSER QUERIES")
        print("=" * 60)
        print("Copy these queries into Neo4j Browser (http://localhost:7474):")
        print()

        queries = [
            ("View all nodes and relationships", "MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 25"),
            ("Show memory network", "MATCH (m:Memory)-[r]->(n) RETURN m,r,n"),
            ("Find file dependencies", "MATCH (f:File)<-[:RELATES_TO]-(m:Memory) RETURN f,m"),
            ("Tag cloud visualization", "MATCH (t:Tag)<-[:TAGGED_WITH]-(m:Memory) RETURN t,m"),
            ("Decision timeline", "MATCH (m:Memory) WHERE m.type = 'decision' RETURN m ORDER BY m.timestamp"),
            ("Most connected files", "MATCH (f:File)<-[:RELATES_TO]-(m:Memory) RETURN f.path, count(m) as connections ORDER BY connections DESC"),
            ("Knowledge graph overview", "MATCH (n) RETURN DISTINCT labels(n), count(n)"),
        ]

        for i, (desc, query) in enumerate(queries, 1):
            print(f"{i}. {desc}:")
            print(f"   {query}")
            print()


def main():
    """Main entry point"""
    try:
        explorer = DatabaseExplorer()
        explorer.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()