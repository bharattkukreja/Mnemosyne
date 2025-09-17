"""Context compression to stay under token limits"""

import logging
import re
from typing import List, Dict, Any
from dataclasses import dataclass

from memory.models import Memory, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class CompressedContext:
    """Compressed context result"""
    content: str
    estimated_tokens: int
    memories_included: int
    memories_excluded: int
    compression_ratio: float


class ContextCompressor:
    """Compresses memory context to fit within token limits"""
    
    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
        
    def compress_memories(
        self, 
        memories: List[SearchResult], 
        current_files: List[str] = None,
        preserve_decisions: bool = True
    ) -> CompressedContext:
        """Compress a list of memories to fit token limit"""
        
        if not memories:
            return CompressedContext(
                content="No relevant memories found.",
                estimated_tokens=5,
                memories_included=0,
                memories_excluded=0,
                compression_ratio=1.0
            )
        
        # Sort memories by priority
        prioritized_memories = self._prioritize_memories(memories, current_files, preserve_decisions)
        
        # Build context incrementally
        context_parts = []
        included_memories = []
        current_tokens = 0
        
        # Reserve tokens for structure and formatting
        reserved_tokens = 200
        available_tokens = self.max_tokens - reserved_tokens
        
        for memory_result in prioritized_memories:
            memory = memory_result.memory
            
            # Estimate tokens for this memory
            memory_content = self._format_memory_content(memory, memory_result.similarity_score)
            memory_tokens = self._estimate_tokens(memory_content)
            
            # Check if we can fit this memory
            if current_tokens + memory_tokens <= available_tokens:
                context_parts.append(memory_content)
                included_memories.append(memory)
                current_tokens += memory_tokens
            else:
                # Try to compress this memory if it's important
                if memory_result.relevance_score > 0.8 or memory.type == "decision":
                    compressed_content = self._compress_memory_content(memory, memory_result.similarity_score)
                    compressed_tokens = self._estimate_tokens(compressed_content)
                    
                    if current_tokens + compressed_tokens <= available_tokens:
                        context_parts.append(compressed_content)
                        included_memories.append(memory)
                        current_tokens += compressed_tokens
                        continue
                
                # Can't fit anymore memories
                break
        
        # Build final context
        if context_parts:
            header = f"## Relevant Context ({len(included_memories)} memories)\n\n"
            content = header + "\n\n".join(context_parts)
        else:
            content = "No memories could fit within token limit."
        
        final_tokens = self._estimate_tokens(content)
        
        return CompressedContext(
            content=content,
            estimated_tokens=final_tokens,
            memories_included=len(included_memories),
            memories_excluded=len(memories) - len(included_memories),
            compression_ratio=len(included_memories) / len(memories) if memories else 1.0
        )
    
    def _prioritize_memories(
        self, 
        memories: List[SearchResult], 
        current_files: List[str] = None,
        preserve_decisions: bool = True
    ) -> List[SearchResult]:
        """Sort memories by importance/relevance"""
        
        def calculate_priority_score(memory_result: SearchResult) -> float:
            memory = memory_result.memory
            score = memory_result.relevance_score
            
            # Boost decisions if preserve_decisions is True
            if preserve_decisions and memory.type == "decision":
                score += 0.3
            
            # Boost memories related to current files
            if current_files:
                file_overlap = len(set(memory.files) & set(current_files))
                if file_overlap > 0:
                    score += 0.2 * file_overlap
            
            # Boost recent memories slightly
            age_days = (memory.timestamp.now() - memory.timestamp).days
            if age_days < 7:
                score += 0.1
            elif age_days < 30:
                score += 0.05
            
            # Boost high-priority TODOs
            if hasattr(memory, 'priority') and memory.priority == "high":
                score += 0.15
            
            return score
        
        # Sort by priority score
        prioritized = sorted(
            memories, 
            key=calculate_priority_score, 
            reverse=True
        )
        
        return prioritized
    
    def _format_memory_content(self, memory: Memory, similarity_score: float) -> str:
        """Format a memory for inclusion in context"""
        
        # Determine emoji based on type
        type_emojis = {
            "decision": "🏗️",
            "todo": "📋",
            "bug_fix": "🐛",
            "rejected_approach": "❌",
            "architecture": "🏛️"
        }
        
        emoji = type_emojis.get(memory.type, "💭")
        
        # Build content
        lines = [
            f"### {emoji} {memory.type.title()}: {memory.content}"
        ]
        
        if memory.reasoning:
            lines.append(f"**Reasoning:** {memory.reasoning}")
        
        if memory.files:
            files_str = ", ".join(memory.files[:3])  # Limit to first 3 files
            if len(memory.files) > 3:
                files_str += f" (+{len(memory.files) - 3} more)"
            lines.append(f"**Files:** {files_str}")
        
        if memory.tags:
            tags_str = ", ".join(memory.tags[:4])  # Limit tags
            lines.append(f"**Tags:** {tags_str}")
        
        # Add metadata
        date_str = memory.timestamp.strftime("%Y-%m-%d")
        lines.append(f"*({date_str}, relevance: {similarity_score:.2f})*")
        
        return "\n".join(lines)
    
    def _compress_memory_content(self, memory: Memory, similarity_score: float) -> str:
        """Create a compressed version of memory content"""
        
        # Shorter format for compressed memories
        emoji = {"decision": "🏗️", "todo": "📋"}.get(memory.type, "💭")
        
        # Truncate long content
        content = memory.content
        if len(content) > 80:
            content = content[:77] + "..."
        
        # Truncate reasoning
        reasoning = memory.reasoning
        if reasoning and len(reasoning) > 60:
            reasoning = reasoning[:57] + "..."
        
        # Build compressed format
        parts = [f"{emoji} {content}"]
        
        if reasoning:
            parts.append(f"({reasoning})")
        
        if memory.files:
            file_list = ", ".join(memory.files[:2])
            if len(memory.files) > 2:
                file_list += f" +{len(memory.files) - 2}"
            parts.append(f"[{file_list}]")
        
        return " ".join(parts)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        
        # Simple estimation: roughly 1 token per 4 characters
        # This is approximate but works for planning
        
        # Count words (more accurate for English text)
        words = len(text.split())
        
        # Average tokens per word is ~1.3 for English
        estimated_tokens = int(words * 1.3)
        
        # Add tokens for formatting (markdown, symbols, etc.)
        formatting_chars = len(re.findall(r'[*_#`\[\](){}]', text))
        estimated_tokens += formatting_chars // 4
        
        return max(estimated_tokens, len(text) // 4)  # Fallback to char-based estimate
    
    def compress_session_context(
        self,
        memories: List[SearchResult],
        current_files: List[str],
        recent_commits: List[str] = None,
        max_tokens: int = None
    ) -> str:
        """Create compressed session context with file and commit info"""
        
        if max_tokens is None:
            max_tokens = self.max_tokens
        
        # Build header with current context
        header_lines = [
            "## 📋 Session Context",
            f"**Current files:** {', '.join(current_files)}"
        ]
        
        if recent_commits:
            commits_str = ", ".join(recent_commits[:3])
            if len(recent_commits) > 3:
                commits_str += f" (+{len(recent_commits) - 3} more)"
            header_lines.append(f"**Recent commits:** {commits_str}")
        
        header_lines.append("")  # Empty line
        
        header = "\n".join(header_lines)
        header_tokens = self._estimate_tokens(header)
        
        # Compress memories with remaining tokens
        remaining_tokens = max_tokens - header_tokens - 50  # Buffer
        
        temp_compressor = ContextCompressor(remaining_tokens)
        compressed = temp_compressor.compress_memories(
            memories, 
            current_files=current_files,
            preserve_decisions=True
        )
        
        # Combine header and compressed memories
        if compressed.memories_included > 0:
            full_context = header + compressed.content
        else:
            full_context = header + "No relevant historical context found."
        
        return full_context