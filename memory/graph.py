"""Neo4j knowledge graph for Mnemosyne memories"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from config import Config
from .models import Memory, Decision, Todo

logger = logging.getLogger(__name__)


@dataclass
class GraphRelationship:
    """Represents a relationship in the knowledge graph"""
    from_node: str
    to_node: str
    relationship_type: str
    properties: Dict[str, Any]


@dataclass 
class GraphQuery:
    """Knowledge graph query parameters"""
    start_node: Optional[str] = None
    relationship_types: Optional[List[str]] = None
    node_types: Optional[List[str]] = None
    max_depth: int = 3
    limit: int = 50


class KnowledgeGraph:
    """Neo4j knowledge graph for memories and relationships"""
    
    def __init__(self, config: Config):
        self.config = config
        self.driver = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Neo4j connection"""
        try:
            from neo4j import GraphDatabase
            
            # Try to connect to Neo4j
            self.driver = GraphDatabase.driver(
                self.config.storage.neo4j_uri,
                auth=(
                    self.config.storage.neo4j_user, 
                    self.config.storage.neo4j_password
                )
            )
            
            # Test connection
            with self.driver.session() as session:
                session.run("MATCH (n) RETURN count(n) as count")
            
            logger.info("Neo4j connection established")
            self._initialize_schema()
            
        except Exception as e:
            logger.warning(f"Neo4j not available: {e}")
            self.driver = None
    
    def _initialize_schema(self):
        """Initialize graph schema with constraints and indexes"""
        if not self.driver:
            return
            
        schema_queries = [
            # Unique constraints
            "CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT file_path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
            "CREATE CONSTRAINT developer_id IF NOT EXISTS FOR (d:Developer) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX memory_type IF NOT EXISTS FOR (m:Memory) ON (m.type)",
            "CREATE INDEX memory_timestamp IF NOT EXISTS FOR (m:Memory) ON (m.timestamp)",
            "CREATE INDEX file_extension IF NOT EXISTS FOR (f:File) ON (f.extension)",
            "CREATE INDEX tag_name IF NOT EXISTS FOR (t:Tag) ON (t.name)",
        ]
        
        try:
            with self.driver.session() as session:
                for query in schema_queries:
                    try:
                        session.run(query)
                    except Exception as e:
                        logger.debug(f"Schema query failed (may already exist): {e}")
            
            logger.info("Neo4j schema initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
    
    def store_memory_in_graph(self, memory: Memory) -> bool:
        """Store memory and its relationships in the knowledge graph"""
        if not self.driver:
            logger.debug("Neo4j not available, skipping graph storage")
            return False
        
        try:
            with self.driver.session() as session:
                # Create memory node
                self._create_memory_node(session, memory)
                
                # Create file relationships
                for file_path in memory.files:
                    self._create_file_relationship(session, memory.id, file_path)
                
                # Create tag relationships
                for tag in memory.tags:
                    self._create_tag_relationship(session, memory.id, tag)
                
                # Create conversation relationship if exists
                if memory.conversation_id:
                    self._create_conversation_relationship(session, memory.id, memory.conversation_id)
                
                # Create developer relationship if exists
                if memory.developer_id:
                    self._create_developer_relationship(session, memory.id, memory.developer_id)
                
                # Create semantic relationships
                self._create_semantic_relationships(session, memory)
            
            logger.info(f"Stored memory {memory.id} in knowledge graph")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory in graph: {e}")
            return False
    
    def _create_memory_node(self, session, memory: Memory):
        """Create memory node in graph"""
        
        # Determine node labels
        labels = ["Memory", memory.type.title()]
        label_str = ":".join(labels)
        
        query = f"""
        MERGE (m:{label_str} {{id: $id}})
        SET m.content = $content,
            m.reasoning = $reasoning,
            m.timestamp = datetime($timestamp),
            m.type = $type,
            m.created_at = datetime()
        """
        
        parameters = {
            "id": memory.id,
            "content": memory.content,
            "reasoning": memory.reasoning,
            "timestamp": memory.timestamp.isoformat(),
            "type": memory.type
        }
        
        # Add type-specific properties
        if isinstance(memory, Decision):
            parameters["decision"] = memory.decision
            if memory.alternatives_considered:
                parameters["alternatives"] = memory.alternatives_considered
        elif isinstance(memory, Todo):
            parameters["task"] = memory.task
            parameters["priority"] = memory.priority
            parameters["status"] = memory.status
            parameters["context"] = memory.context
        
        session.run(query, parameters)
    
    def _create_file_relationship(self, session, memory_id: str, file_path: str):
        """Create relationship between memory and file"""
        
        # Extract file info
        path_parts = file_path.split('/')
        filename = path_parts[-1]
        directory = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ""
        extension = filename.split('.')[-1] if '.' in filename else ""
        
        query = """
        MERGE (f:File {path: $file_path})
        SET f.filename = $filename,
            f.directory = $directory,
            f.extension = $extension,
            f.created_at = coalesce(f.created_at, datetime())
        WITH f
        MATCH (m:Memory {id: $memory_id})
        MERGE (m)-[:RELATES_TO]->(f)
        """
        
        session.run(query, {
            "memory_id": memory_id,
            "file_path": file_path,
            "filename": filename,
            "directory": directory,
            "extension": extension
        })
    
    def _create_tag_relationship(self, session, memory_id: str, tag: str):
        """Create relationship between memory and tag"""
        
        query = """
        MERGE (t:Tag {name: $tag})
        SET t.created_at = coalesce(t.created_at, datetime())
        WITH t
        MATCH (m:Memory {id: $memory_id})
        MERGE (m)-[:TAGGED_WITH]->(t)
        """
        
        session.run(query, {
            "memory_id": memory_id,
            "tag": tag
        })
    
    def _create_conversation_relationship(self, session, memory_id: str, conversation_id: str):
        """Create relationship between memory and conversation"""
        
        query = """
        MERGE (c:Conversation {id: $conversation_id})
        SET c.created_at = coalesce(c.created_at, datetime())
        WITH c
        MATCH (m:Memory {id: $memory_id})
        MERGE (c)-[:CONTAINS]->(m)
        """
        
        session.run(query, {
            "memory_id": memory_id,
            "conversation_id": conversation_id
        })
    
    def _create_developer_relationship(self, session, memory_id: str, developer_id: str):
        """Create relationship between memory and developer"""
        
        query = """
        MERGE (d:Developer {id: $developer_id})
        SET d.created_at = coalesce(d.created_at, datetime())
        WITH d
        MATCH (m:Memory {id: $memory_id})
        MERGE (d)-[:AUTHORED]->(m)
        """
        
        session.run(query, {
            "memory_id": memory_id,
            "developer_id": developer_id
        })
    
    def _create_semantic_relationships(self, session, memory: Memory):
        """Create semantic relationships between memories"""
        
        # Find related memories by content similarity and create relationships
        # This would use the vector similarity from ChromaDB to inform graph relationships
        
        query = """
        MATCH (m1:Memory {id: $memory_id})
        MATCH (m2:Memory) 
        WHERE m1 <> m2 
        AND (
            any(file IN m1.files WHERE file IN m2.files) OR
            any(tag IN m1.tags WHERE tag IN m2.tags) OR
            m1.type = m2.type
        )
        WITH m1, m2, 
             size([file IN m1.files WHERE file IN m2.files]) as file_overlap,
             size([tag IN m1.tags WHERE tag IN m2.tags]) as tag_overlap
        WHERE file_overlap > 0 OR tag_overlap > 0
        MERGE (m1)-[r:RELATED_TO]->(m2)
        SET r.file_overlap = file_overlap,
            r.tag_overlap = tag_overlap,
            r.strength = (file_overlap * 0.6 + tag_overlap * 0.4),
            r.created_at = datetime()
        """
        
        # Note: In a real implementation, we'd use vector similarity scores here
        # For now, we use file and tag overlap as a proxy
        session.run(query, {"memory_id": memory.id})
    
    def find_related_memories(self, memory_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Find memories related to a given memory through graph relationships"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (start:Memory {id: $memory_id})
                MATCH path = (start)-[*1..$max_depth]-(related:Memory)
                WHERE start <> related
                WITH related, relationships(path) as rels, length(path) as depth
                RETURN DISTINCT related.id as id,
                       related.content as content,
                       related.type as type,
                       related.timestamp as timestamp,
                       depth,
                       [r in rels | type(r)] as relationship_path
                ORDER BY depth, related.timestamp DESC
                LIMIT 20
                """
                
                result = session.run(query, {
                    "memory_id": memory_id,
                    "max_depth": max_depth
                })
                
                related_memories = []
                for record in result:
                    related_memories.append({
                        "id": record["id"],
                        "content": record["content"],
                        "type": record["type"],
                        "timestamp": record["timestamp"],
                        "depth": record["depth"],
                        "relationship_path": record["relationship_path"]
                    })
                
                return related_memories
                
        except Exception as e:
            logger.error(f"Failed to find related memories: {e}")
            return []
    
    def get_file_evolution(self, file_path: str) -> List[Dict[str, Any]]:
        """Get the evolution of decisions and TODOs for a specific file"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (f:File {path: $file_path})<-[:RELATES_TO]-(m:Memory)
                OPTIONAL MATCH (m)<-[:CONTAINS]-(c:Conversation)
                RETURN m.id as id,
                       m.content as content,
                       m.type as type,
                       m.timestamp as timestamp,
                       m.reasoning as reasoning,
                       c.id as conversation_id
                ORDER BY m.timestamp ASC
                """
                
                result = session.run(query, {"file_path": file_path})
                
                evolution = []
                for record in result:
                    evolution.append({
                        "id": record["id"],
                        "content": record["content"],
                        "type": record["type"],
                        "timestamp": record["timestamp"],
                        "reasoning": record["reasoning"],
                        "conversation_id": record["conversation_id"]
                    })
                
                return evolution
                
        except Exception as e:
            logger.error(f"Failed to get file evolution: {e}")
            return []
    
    def get_decision_impact(self, decision_id: str) -> Dict[str, Any]:
        """Analyze the impact of a decision across files and subsequent decisions"""
        if not self.driver:
            return {}
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (decision:Decision {id: $decision_id})
                
                // Find affected files
                MATCH (decision)-[:RELATES_TO]->(file:File)
                
                // Find subsequent memories on those files
                MATCH (file)<-[:RELATES_TO]-(subsequent:Memory)
                WHERE subsequent.timestamp > decision.timestamp
                
                // Find related decisions
                MATCH (decision)-[:RELATED_TO*1..2]-(related:Decision)
                WHERE related <> decision
                
                RETURN decision.content as decision_content,
                       collect(DISTINCT file.path) as affected_files,
                       collect(DISTINCT {
                           id: subsequent.id,
                           content: subsequent.content,
                           type: subsequent.type,
                           timestamp: subsequent.timestamp
                       }) as subsequent_changes,
                       collect(DISTINCT {
                           id: related.id,
                           content: related.content,
                           timestamp: related.timestamp
                       }) as related_decisions
                """
                
                result = session.run(query, {"decision_id": decision_id})
                record = result.single()
                
                if record:
                    return {
                        "decision_content": record["decision_content"],
                        "affected_files": record["affected_files"],
                        "subsequent_changes": record["subsequent_changes"],
                        "related_decisions": record["related_decisions"]
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Failed to analyze decision impact: {e}")
            return {}
    
    def find_knowledge_patterns(self) -> Dict[str, Any]:
        """Discover patterns in the knowledge graph"""
        if not self.driver:
            return {}
        
        try:
            with self.driver.session() as session:
                # Most connected files
                files_query = """
                MATCH (f:File)<-[:RELATES_TO]-(m:Memory)
                WITH f, count(m) as memory_count
                ORDER BY memory_count DESC
                LIMIT 10
                RETURN f.path as file_path, memory_count
                """
                
                # Most used tags
                tags_query = """
                MATCH (t:Tag)<-[:TAGGED_WITH]-(m:Memory)
                WITH t, count(m) as usage_count
                ORDER BY usage_count DESC
                LIMIT 10
                RETURN t.name as tag_name, usage_count
                """
                
                # Decision chains
                chains_query = """
                MATCH path = (d1:Decision)-[:RELATED_TO*1..3]->(d2:Decision)
                WHERE d1 <> d2
                RETURN length(path) as chain_length, count(*) as chain_count
                ORDER BY chain_length
                """
                
                files_result = list(session.run(files_query))
                tags_result = list(session.run(tags_query))
                chains_result = list(session.run(chains_query))
                
                return {
                    "most_active_files": [
                        {"file": r["file_path"], "memories": r["memory_count"]} 
                        for r in files_result
                    ],
                    "popular_tags": [
                        {"tag": r["tag_name"], "usage": r["usage_count"]} 
                        for r in tags_result
                    ],
                    "decision_chains": [
                        {"length": r["chain_length"], "count": r["chain_count"]} 
                        for r in chains_result
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to find knowledge patterns: {e}")
            return {}
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")