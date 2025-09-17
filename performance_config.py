"""Performance optimizations for real-time Cursor integration"""

import logging
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """Performance tuning configuration"""

    # Memory limits
    max_memory_cache_size: int = 1000  # Max memories to keep in RAM
    context_cache_ttl: int = 300  # Context cache TTL in seconds

    # Search optimizations
    fast_search_limit: int = 5  # Limit results for fast queries
    embedding_cache_size: int = 500  # Cache embeddings for recent queries

    # Response time targets
    tool_response_timeout: float = 5.0  # Max seconds for tool responses
    context_injection_timeout: float = 2.0  # Max seconds for context injection

    # Batch processing
    batch_storage_enabled: bool = True  # Batch multiple memory stores
    batch_size: int = 10  # Max items per batch
    batch_timeout: float = 1.0  # Max seconds to wait for batch

    # Connection pooling
    neo4j_pool_size: int = 5  # Neo4j connection pool size
    chromadb_pool_size: int = 3  # ChromaDB connection pool size


class PerformanceOptimizer:
    """Runtime performance optimizations for Mnemosyne"""

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self._memory_cache = {}
        self._context_cache = {}
        self._embedding_cache = {}
        self._batch_queue = []

    def optimize_for_cursor(self) -> Dict[str, Any]:
        """Apply optimizations specifically for Cursor integration"""

        optimizations = {
            "storage": {
                "lazy_loading": True,
                "connection_pooling": True,
                "cache_embeddings": True,
            },
            "search": {
                "result_limit": self.config.fast_search_limit,
                "relevance_threshold": 0.7,  # Higher threshold for speed
                "context_compression": True,
            },
            "tools": {
                "timeout": self.config.tool_response_timeout,
                "async_processing": True,
                "batch_operations": self.config.batch_storage_enabled,
            },
        }

        logger.info("Applied Cursor performance optimizations")
        return optimizations

    def get_fast_context_config(self) -> Dict[str, Any]:
        """Get configuration for fast context injection"""

        return {
            "max_injection_tokens": 1500,  # Reduced for speed
            "max_memories_per_query": 3,  # Fewer memories for speed
            "relevance_threshold": 0.8,  # Higher threshold
            "include_file_overlap_only": True,  # Only file-related memories
        }

    def get_search_config(self) -> Dict[str, Any]:
        """Get configuration for fast search responses"""

        return {
            "max_results": self.config.fast_search_limit,
            "similarity_threshold": 0.7,
            "enable_caching": True,
            "cache_ttl": self.config.context_cache_ttl,
        }


# Performance-optimized configuration for real-time use
CURSOR_PERFORMANCE_CONFIG = PerformanceConfig(
    max_memory_cache_size=500,  # Smaller cache for responsiveness
    context_cache_ttl=180,  # 3-minute cache
    fast_search_limit=3,  # Only top 3 results
    tool_response_timeout=3.0,  # 3-second timeout
    context_injection_timeout=1.5,  # 1.5-second context injection
    batch_storage_enabled=False,  # Disable batching for real-time feel
)

# Standard configuration for balanced performance
BALANCED_PERFORMANCE_CONFIG = PerformanceConfig(
    max_memory_cache_size=1000,
    context_cache_ttl=300,
    fast_search_limit=5,
    tool_response_timeout=5.0,
    context_injection_timeout=2.0,
    batch_storage_enabled=True,
)

# High-throughput configuration for batch processing
BATCH_PERFORMANCE_CONFIG = PerformanceConfig(
    max_memory_cache_size=2000,
    context_cache_ttl=600,
    fast_search_limit=10,
    tool_response_timeout=10.0,
    context_injection_timeout=5.0,
    batch_storage_enabled=True,
    batch_size=20,
)
