"""Advanced relevance scoring for memory retrieval"""

import logging
from typing import List, Set, Dict, Any
from datetime import datetime, timedelta
from memory.models import Memory, SearchResult

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Advanced relevance scoring for memory retrieval"""
    
    def __init__(self):
        self.weights = {
            'semantic_similarity': 0.4,
            'file_overlap': 0.3,
            'recency': 0.15,
            'type_relevance': 0.1,
            'tag_overlap': 0.05
        }
    
    def score_memories(
        self,
        memories: List[SearchResult],
        query_context: Dict[str, Any]
    ) -> List[SearchResult]:
        """Score and re-rank memories based on context"""
        
        current_files = query_context.get('current_files', [])
        recent_commits = query_context.get('recent_commits', [])
        query_intent = query_context.get('intent', 'general')  # search, context, file_history
        query_tags = query_context.get('tags', [])
        
        scored_memories = []
        
        for memory_result in memories:
            memory = memory_result.memory
            
            # Start with base similarity score
            total_score = memory_result.similarity_score * self.weights['semantic_similarity']
            
            # Add file overlap score
            file_score = self._calculate_file_overlap_score(memory, current_files)
            total_score += file_score * self.weights['file_overlap']
            
            # Add recency score
            recency_score = self._calculate_recency_score(memory)
            total_score += recency_score * self.weights['recency']
            
            # Add type relevance score
            type_score = self._calculate_type_relevance_score(memory, query_intent)
            total_score += type_score * self.weights['type_relevance']
            
            # Add tag overlap score
            tag_score = self._calculate_tag_overlap_score(memory, query_tags)
            total_score += tag_score * self.weights['tag_overlap']
            
            # Create new SearchResult with updated relevance score
            scored_result = SearchResult(
                memory=memory,
                similarity_score=memory_result.similarity_score,
                relevance_score=min(total_score, 1.0)  # Cap at 1.0
            )
            
            scored_memories.append(scored_result)
        
        # Sort by relevance score
        scored_memories.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return scored_memories
    
    def _calculate_file_overlap_score(self, memory: Memory, current_files: List[str]) -> float:
        """Calculate score based on file overlap"""
        
        if not current_files or not memory.files:
            return 0.0
        
        # Direct file matches
        memory_files_set = set(memory.files)
        current_files_set = set(current_files)
        
        direct_overlap = len(memory_files_set & current_files_set)
        if direct_overlap > 0:
            return min(direct_overlap / len(current_files_set), 1.0)
        
        # Partial matches (same directory, similar names)
        partial_score = 0.0
        
        for current_file in current_files:
            current_dir = '/'.join(current_file.split('/')[:-1])
            current_name = current_file.split('/')[-1]
            current_ext = current_name.split('.')[-1] if '.' in current_name else ''
            
            for memory_file in memory.files:
                memory_dir = '/'.join(memory_file.split('/')[:-1])
                memory_name = memory_file.split('/')[-1]
                memory_ext = memory_name.split('.')[-1] if '.' in memory_name else ''
                
                # Same directory
                if current_dir and memory_dir and current_dir == memory_dir:
                    partial_score += 0.3
                
                # Same file extension
                if current_ext and memory_ext and current_ext == memory_ext:
                    partial_score += 0.1
                
                # Similar filenames
                if current_name and memory_name:
                    name_similarity = self._calculate_string_similarity(current_name, memory_name)
                    if name_similarity > 0.6:
                        partial_score += 0.2 * name_similarity
        
        return min(partial_score, 0.8)  # Cap partial matches lower than direct matches
    
    def _calculate_recency_score(self, memory: Memory) -> float:
        """Calculate score based on recency"""
        
        now = datetime.now()
        age = now - memory.timestamp
        
        # Score decreases with age
        if age <= timedelta(days=1):
            return 1.0
        elif age <= timedelta(days=7):
            return 0.8
        elif age <= timedelta(days=30):
            return 0.6
        elif age <= timedelta(days=90):
            return 0.4
        elif age <= timedelta(days=365):
            return 0.2
        else:
            return 0.1
    
    def _calculate_type_relevance_score(self, memory: Memory, query_intent: str) -> float:
        """Calculate score based on memory type and query intent"""
        
        # Intent-based scoring
        intent_scores = {
            'search': {
                'decision': 0.9,
                'todo': 0.8,
                'bug_fix': 0.7,
                'rejected_approach': 0.6,
                'architecture': 0.9
            },
            'context': {
                'decision': 1.0,  # Decisions are crucial for context
                'todo': 0.6,
                'bug_fix': 0.5,
                'rejected_approach': 0.7,  # Important to know what not to do
                'architecture': 1.0
            },
            'file_history': {
                'decision': 0.8,
                'todo': 0.9,  # TODOs are important for file history
                'bug_fix': 0.9,
                'rejected_approach': 0.5,
                'architecture': 0.7
            }
        }
        
        return intent_scores.get(query_intent, {}).get(memory.type, 0.5)
    
    def _calculate_tag_overlap_score(self, memory: Memory, query_tags: List[str]) -> float:
        """Calculate score based on tag overlap"""
        
        if not query_tags or not memory.tags:
            return 0.0
        
        memory_tags_set = set(tag.lower() for tag in memory.tags)
        query_tags_set = set(tag.lower() for tag in query_tags)
        
        overlap = len(memory_tags_set & query_tags_set)
        
        if overlap == 0:
            return 0.0
        
        # Jaccard similarity
        union = len(memory_tags_set | query_tags_set)
        return overlap / union if union > 0 else 0.0
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        
        if not str1 or not str2:
            return 0.0
        
        str1 = str1.lower()
        str2 = str2.lower()
        
        if str1 == str2:
            return 1.0
        
        # Simple character-based similarity
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
        
        # Count matching characters at same positions
        matches = sum(1 for i, c in enumerate(str1) if i < len(str2) and c == str2[i])
        
        return matches / max_len
    
    def get_context_memories(
        self,
        all_memories: List[SearchResult],
        current_files: List[str],
        recent_commits: List[str] = None,
        max_memories: int = 5
    ) -> List[SearchResult]:
        """Get the most relevant memories for session context"""
        
        query_context = {
            'current_files': current_files,
            'recent_commits': recent_commits or [],
            'intent': 'context',
            'tags': self._extract_tags_from_files(current_files)
        }
        
        # Score all memories
        scored_memories = self.score_memories(all_memories, query_context)
        
        # Apply context-specific filtering
        context_memories = []
        
        # Prioritize decisions related to current files
        decisions = [m for m in scored_memories if m.memory.type == "decision"]
        context_memories.extend(decisions[:max_memories // 2])
        
        # Add other relevant memories
        remaining_slots = max_memories - len(context_memories)
        other_memories = [m for m in scored_memories if m not in context_memories]
        context_memories.extend(other_memories[:remaining_slots])
        
        return context_memories
    
    def _extract_tags_from_files(self, files: List[str]) -> List[str]:
        """Extract relevant tags from file paths"""
        
        tags = []
        
        for file in files:
            # Extract from file extension
            if '.' in file:
                ext = file.split('.')[-1].lower()
                if ext in ['py', 'js', 'ts', 'jsx', 'tsx']:
                    tags.append('frontend' if ext in ['js', 'jsx', 'ts', 'tsx'] else 'backend')
                elif ext in ['sql']:
                    tags.append('database')
                elif ext in ['css', 'scss', 'sass']:
                    tags.append('styling')
                elif ext in ['md', 'txt']:
                    tags.append('documentation')
            
            # Extract from path components
            path_parts = file.lower().split('/')
            for part in path_parts:
                if part in ['api', 'routes', 'endpoints']:
                    tags.append('api')
                elif part in ['db', 'database', 'models']:
                    tags.append('database')
                elif part in ['auth', 'security']:
                    tags.append('security')
                elif part in ['test', 'tests', 'spec']:
                    tags.append('testing')
                elif part in ['ui', 'components', 'frontend']:
                    tags.append('frontend')
                elif part in ['server', 'backend', 'service']:
                    tags.append('backend')
        
        return list(set(tags))  # Remove duplicates