"""Storage layer for Mnemosyne memories"""

import json
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from config import Config
from .models import Memory, Decision, Todo, CodeContext, SearchQuery, SearchResult
from .embeddings import EmbeddingGenerator
from .graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class MemoryStorage:
    """Storage backend for memories"""

    def __init__(self, config: Config):
        self.config = config
        self.embedding_generator = EmbeddingGenerator(config)
        self.knowledge_graph = KnowledgeGraph(config)
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage backend"""
        try:
            # Try ChromaDB first
            try:
                import chromadb
                from chromadb.config import Settings

                # Initialize ChromaDB
                storage_path = self.config.storage.vector_db_path
                Path(storage_path).mkdir(parents=True, exist_ok=True)

                self.chroma_client = chromadb.PersistentClient(
                    path=storage_path, settings=Settings(anonymized_telemetry=False)
                )

                # Get or create collection
                self.collection = self.chroma_client.get_or_create_collection(
                    name="memories", metadata={"description": "Mnemosyne memory storage"}
                )

                self.storage_type = "chromadb"
                logger.info("ChromaDB storage initialized")

            except ImportError:
                logger.warning("ChromaDB not available, using file-based storage")
                self._initialize_file_storage()

        except Exception as e:
            logger.error(f"Storage initialization failed: {e}")
            self._initialize_file_storage()

    def _initialize_file_storage(self):
        """Initialize simple file-based storage as fallback"""
        self.storage_type = "file"
        self.storage_dir = Path(self.config.storage.vector_db_path).parent / "file_storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memories_file = self.storage_dir / "memories.jsonl"
        logger.info(f"File storage initialized at {self.storage_dir}")

    def store_memory(self, memory: Memory) -> str:
        """Store a memory item"""
        try:
            # Generate embedding
            full_text = f"{memory.content} {memory.reasoning} {' '.join(memory.tags)}"
            memory.embedding = self.embedding_generator.generate_embedding(full_text)

            # Store in primary storage (ChromaDB or file)
            if self.storage_type == "chromadb":
                memory_id = self._store_chromadb(memory)
            else:
                memory_id = self._store_file(memory)

            # Store in knowledge graph
            self.knowledge_graph.store_memory_in_graph(memory)

            return memory_id

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise

    def _store_chromadb(self, memory: Memory) -> str:
        """Store memory in ChromaDB"""
        self.collection.add(
            ids=[memory.id],
            embeddings=[memory.embedding],
            metadatas=[
                {
                    "type": memory.type,
                    "files": json.dumps(memory.files),
                    "tags": json.dumps(memory.tags),
                    "timestamp": memory.timestamp.isoformat(),
                    "conversation_id": memory.conversation_id or "",
                    "developer_id": memory.developer_id or "",
                    "session_id": memory.session_id or "",
                }
            ],
            documents=[f"{memory.content} | {memory.reasoning}"],
        )

        logger.info(f"Stored memory {memory.id} in ChromaDB")
        return memory.id

    def _store_file(self, memory: Memory) -> str:
        """Store memory in file system"""
        memory_data = memory.model_dump()
        memory_data["timestamp"] = memory.timestamp.isoformat()

        with open(self.memories_file, "a") as f:
            f.write(json.dumps(memory_data) + "\n")

        logger.info(f"Stored memory {memory.id} in file storage")
        return memory.id

    def search_memories(self, query: SearchQuery) -> List[SearchResult]:
        """Search for memories"""
        try:
            query_embedding = self.embedding_generator.generate_embedding(query.query)

            if self.storage_type == "chromadb":
                return self._search_chromadb(query, query_embedding)
            else:
                return self._search_file(query, query_embedding)

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _search_chromadb(
        self, query: SearchQuery, query_embedding: List[float]
    ) -> List[SearchResult]:
        """Search ChromaDB"""
        # Build where clause for filters
        where_clause = {}
        if "type" in query.filters and query.filters["type"] != "all":
            where_clause["type"] = query.filters["type"]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=query.max_results,
            where=where_clause if where_clause else None,
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                # Reconstruct memory from stored data
                metadata = results["metadatas"][0][i]
                document = results["documents"][0][i]
                distance = results["distances"][0][i] if results.get("distances") else 0.0

                # Parse document back to content/reasoning
                parts = document.split(" | ", 1)
                content = parts[0]
                reasoning = parts[1] if len(parts) > 1 else ""

                memory = Memory(
                    id=memory_id,
                    type=metadata["type"],
                    content=content,
                    reasoning=reasoning,
                    files=json.loads(metadata["files"]),
                    tags=json.loads(metadata["tags"]),
                    timestamp=datetime.fromisoformat(metadata["timestamp"]),
                    conversation_id=metadata.get("conversation_id"),
                    developer_id=metadata.get("developer_id"),
                    session_id=metadata.get("session_id"),
                )

                similarity_score = 1.0 - distance  # Convert distance to similarity

                search_results.append(
                    SearchResult(
                        memory=memory,
                        similarity_score=similarity_score,
                        relevance_score=similarity_score,  # Simple relevance for now
                    )
                )

        return search_results

    def _search_file(self, query: SearchQuery, query_embedding: List[float]) -> List[SearchResult]:
        """Search file storage"""
        if not self.memories_file.exists():
            return []

        search_results = []

        with open(self.memories_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())

                    # Apply filters
                    if "type" in query.filters and query.filters["type"] != "all":
                        if data.get("type") != query.filters["type"]:
                            continue

                    # Reconstruct memory
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    memory = Memory(**data)

                    # Calculate similarity
                    if memory.embedding:
                        similarity = self.embedding_generator.compute_similarity(
                            query_embedding, memory.embedding
                        )

                        if similarity >= query.similarity_threshold:
                            search_results.append(
                                SearchResult(
                                    memory=memory,
                                    similarity_score=similarity,
                                    relevance_score=similarity,
                                )
                            )

                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to parse memory line: {e}")
                    continue

        # Sort by similarity and limit results
        search_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return search_results[: query.max_results]

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a specific memory by ID"""
        if self.storage_type == "chromadb":
            try:
                result = self.collection.get(ids=[memory_id])
                if result["ids"]:
                    # Reconstruct memory from ChromaDB data
                    metadata = result["metadatas"][0]
                    document = result["documents"][0]

                    parts = document.split(" | ", 1)
                    content = parts[0]
                    reasoning = parts[1] if len(parts) > 1 else ""

                    return Memory(
                        id=memory_id,
                        type=metadata["type"],
                        content=content,
                        reasoning=reasoning,
                        files=json.loads(metadata["files"]),
                        tags=json.loads(metadata["tags"]),
                        timestamp=datetime.fromisoformat(metadata["timestamp"]),
                        conversation_id=metadata.get("conversation_id"),
                        developer_id=metadata.get("developer_id"),
                        session_id=metadata.get("session_id"),
                    )
            except Exception as e:
                logger.error(f"Failed to get memory {memory_id}: {e}")

        else:
            # Search file storage
            if self.memories_file.exists():
                with open(self.memories_file, "r") as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if data.get("id") == memory_id:
                                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                                return Memory(**data)
                        except Exception:
                            continue

        return None

    def get_all_memories(self) -> List[SearchResult]:
        """Get all stored memories for context analysis"""
        try:
            if self.storage_type == "chromadb":
                return self._get_all_chromadb()
            else:
                return self._get_all_file()
        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            return []

    def _get_all_chromadb(self) -> List[SearchResult]:
        """Get all memories from ChromaDB"""
        try:
            # Get all documents from collection
            result = self.collection.get(include=["documents", "metadatas", "embeddings"])

            memories = []
            for i, doc in enumerate(result["documents"]):
                metadata = result["metadatas"][i] if result["metadatas"] else {}

                # Parse document format: "content | reasoning"
                parts = doc.split(" | ", 1)
                content = parts[0]
                reasoning = parts[1] if len(parts) > 1 else ""

                # Parse JSON stored metadata
                try:
                    files = json.loads(metadata.get("files", "[]")) if metadata.get("files") else []
                except:
                    files = []

                try:
                    tags = json.loads(metadata.get("tags", "[]")) if metadata.get("tags") else []
                except:
                    tags = []

                # Reconstruct memory from metadata
                memory = Memory(
                    id=result["ids"][i] if result["ids"] else f"mem_{i}",
                    type=metadata.get("type", "unknown"),
                    content=content,
                    reasoning=reasoning,
                    files=files,
                    tags=tags,
                    timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
                    author=metadata.get("author", "unknown")
                )

                # Create SearchResult with neutral relevance score
                search_result = SearchResult(
                    memory=memory,
                    similarity_score=0.5,  # Neutral score for all memories
                    relevance_score=0.5
                )
                memories.append(search_result)

            return memories

        except Exception as e:
            logger.error(f"Failed to get all memories from ChromaDB: {e}")
            return []

    def _get_all_file(self) -> List[SearchResult]:
        """Get all memories from file storage"""
        try:
            storage_dir = Path(self.config.storage.vector_db_path)
            memories = []

            for file_path in storage_dir.glob("*.json"):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)

                    memory = Memory(**data)
                    search_result = SearchResult(
                        memory=memory,
                        similarity_score=0.5,  # Neutral score
                        relevance_score=0.5
                    )
                    memories.append(search_result)

                except Exception as e:
                    logger.warning(f"Failed to load memory from {file_path}: {e}")
                    continue

            return memories

        except Exception as e:
            logger.error(f"Failed to get all memories from file storage: {e}")
            return []

    def get_related_memories(self, memory_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Get memories related through knowledge graph relationships"""
        return self.knowledge_graph.find_related_memories(memory_id, max_depth)

    def get_file_evolution(self, file_path: str) -> List[Dict[str, Any]]:
        """Get the chronological evolution of memories for a file"""
        return self.knowledge_graph.get_file_evolution(file_path)

    def analyze_decision_impact(self, decision_id: str) -> Dict[str, Any]:
        """Analyze the impact and influence of a decision"""
        return self.knowledge_graph.get_decision_impact(decision_id)

    def discover_knowledge_patterns(self) -> Dict[str, Any]:
        """Discover patterns and insights from the knowledge graph"""
        return self.knowledge_graph.find_knowledge_patterns()

    def get_memories_by_session(self, session_id: str) -> List[SearchResult]:
        """Get all memories from a specific session"""
        try:
            if self.storage_type == "chromadb":
                return self._get_session_memories_chromadb(session_id)
            else:
                return self._get_session_memories_file(session_id)
        except Exception as e:
            logger.error(f"Failed to get memories for session {session_id}: {e}")
            return []

    def _get_session_memories_chromadb(self, session_id: str) -> List[SearchResult]:
        """Get session memories from ChromaDB"""
        results = self.collection.query(
            query_embeddings=[[0.0] * self.config.embeddings.dimension],  # Dummy embedding
            n_results=1000,  # Large number to get all results
            where={"session_id": session_id},
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                document = results["documents"][0][i]

                # Parse document back to content/reasoning
                parts = document.split(" | ", 1)
                content = parts[0]
                reasoning = parts[1] if len(parts) > 1 else ""

                memory = Memory(
                    id=memory_id,
                    type=metadata["type"],
                    content=content,
                    reasoning=reasoning,
                    files=json.loads(metadata["files"]),
                    tags=json.loads(metadata["tags"]),
                    timestamp=datetime.fromisoformat(metadata["timestamp"]),
                    conversation_id=metadata.get("conversation_id"),
                    developer_id=metadata.get("developer_id"),
                    session_id=metadata.get("session_id"),
                )

                search_results.append(
                    SearchResult(
                        memory=memory,
                        similarity_score=1.0,  # Exact match
                        relevance_score=1.0,
                    )
                )

        # Sort by timestamp for chronological order
        search_results.sort(key=lambda x: x.memory.timestamp)
        return search_results

    def _get_session_memories_file(self, session_id: str) -> List[SearchResult]:
        """Get session memories from file storage"""
        if not self.memories_file.exists():
            return []

        search_results = []
        with open(self.memories_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get("session_id") == session_id:
                        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                        memory = Memory(**data)

                        search_results.append(
                            SearchResult(
                                memory=memory,
                                similarity_score=1.0,
                                relevance_score=1.0,
                            )
                        )
                except Exception:
                    continue

        # Sort by timestamp for chronological order
        search_results.sort(key=lambda x: x.memory.timestamp)
        return search_results

    def update_todo_status(self, todo_id: str, new_status: str) -> bool:
        """Update the status of a TODO memory"""
        try:
            if self.storage_type == "chromadb":
                return self._update_todo_status_chromadb(todo_id, new_status)
            else:
                return self._update_todo_status_file(todo_id, new_status)
        except Exception as e:
            logger.error(f"Failed to update TODO status: {e}")
            return False

    def _update_todo_status_chromadb(self, todo_id: str, new_status: str) -> bool:
        """Update TODO status in ChromaDB"""
        try:
            # Get the existing memory
            result = self.collection.get(ids=[todo_id])
            if not result["ids"]:
                return False

            # Get current metadata
            metadata = result["metadatas"][0]
            document = result["documents"][0]

            # Check if it's a TODO
            if metadata.get("type") != "todo":
                logger.warning(f"Memory {todo_id} is not a TODO")
                return False

            # Update metadata with new status
            updated_metadata = metadata.copy()
            updated_metadata["status"] = new_status

            # ChromaDB doesn't support updates, so we need to delete and re-add
            self.collection.delete(ids=[todo_id])

            # Re-add with updated metadata
            embedding = result["embeddings"][0] if result.get("embeddings") else None
            if embedding is None:
                # Regenerate embedding if not available
                embedding = self.embedding_generator.generate_embedding(document)

            self.collection.add(
                ids=[todo_id],
                embeddings=[embedding],
                metadatas=[updated_metadata],
                documents=[document]
            )

            logger.info(f"Updated TODO {todo_id} status to {new_status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update TODO in ChromaDB: {e}")
            return False

    def _update_todo_status_file(self, todo_id: str, new_status: str) -> bool:
        """Update TODO status in file storage"""
        try:
            if not self.memories_file.exists():
                return False

            updated_lines = []
            found = False

            # Read all lines and update the matching TODO
            with open(self.memories_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get("id") == todo_id and data.get("type") == "todo":
                            data["status"] = new_status
                            found = True
                        updated_lines.append(json.dumps(data))
                    except Exception:
                        updated_lines.append(line.strip())

            if found:
                # Write back all lines
                with open(self.memories_file, "w") as f:
                    for line in updated_lines:
                        f.write(line + "\n")
                logger.info(f"Updated TODO {todo_id} status to {new_status}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to update TODO in file storage: {e}")
            return False
