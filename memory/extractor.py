"""Extract structured memories from conversation text"""

import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import Decision, Todo, Memory

logger = logging.getLogger(__name__)


class ConversationExtractor:
    """Extracts decisions, TODOs, and other memories from conversation text"""
    
    def __init__(self):
        self.decision_patterns = [
            # Direct decision statements
            r"(?:let['']s|we['']ll|i['']ll|we should|let's|decided to|going to|will)\s+(?:use|choose|implement|go with|adopt)\s+([^.!?\n]+)",
            r"(?:decision|choice):\s*([^.!?\n]+)",
            r"(?:we['']re using|using|chose|picked|selected)\s+([^.!?\n]+)",
            # Architecture decisions
            r"(?:for|as) (?:the|our) (?:database|framework|library|api|backend|frontend),?\s*(?:we['']ll|let['']s|we should|we're)\s*(?:use|go with|choose)\s+([^.!?\n]+)",
        ]
        
        self.todo_patterns = [
            # TODO/task statements
            r"(?:todo|task|need to|should|must|have to|let['']s|we need to)\s+([^.!?\n]+)",
            r"(?:next|later|tomorrow|future),?\s*(?:we|i)['']?(?:ll|will|need to|should)\s+([^.!?\n]+)",
            r"(?:remaining|left to do|still need to)\s*:?\s*([^.!?\n]+)",
            # Action items
            r"(?:action|item|follow[- ]?up):\s*([^.!?\n]+)",
        ]
        
        self.rejection_patterns = [
            r"(?:not|don['']t|won['']t|shouldn['']t|avoid|skip)\s+(?:using|going with|choosing)\s+([^.!?\n]+)",
            r"(?:decided against|rejected|ruled out)\s+([^.!?\n]+)",
            r"([^.!?\n]+)\s+(?:is|was|would be)\s+(?:too|not|bad|problematic)",
        ]

    def extract_from_conversation(
        self, 
        conversation_text: str, 
        conversation_id: Optional[str] = None,
        context_files: Optional[List[str]] = None
    ) -> List[Memory]:
        """Extract all memories from a conversation"""
        
        memories = []
        
        # Split into messages (simple approach)
        messages = self._split_messages(conversation_text)
        
        for i, message in enumerate(messages):
            # Extract decisions
            decisions = self._extract_decisions(message, conversation_id, context_files)
            memories.extend(decisions)
            
            # Extract TODOs
            todos = self._extract_todos(message, conversation_id, context_files)
            memories.extend(todos)
            
            # Extract rejections as decisions with special tags
            rejections = self._extract_rejections(message, conversation_id, context_files)
            memories.extend(rejections)
        
        # Deduplicate similar memories
        memories = self._deduplicate_memories(memories)
        
        logger.info(f"Extracted {len(memories)} memories from conversation")
        return memories

    def _split_messages(self, conversation_text: str) -> List[str]:
        """Split conversation into individual messages"""
        # Simple splitting - could be enhanced with better parsing
        lines = conversation_text.split('\n')
        messages = []
        current_message = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_message:
                    messages.append('\n'.join(current_message))
                    current_message = []
            else:
                # Look for speaker indicators
                if re.match(r'^(user|human|assistant|claude|ai):', line.lower()):
                    if current_message:
                        messages.append('\n'.join(current_message))
                    current_message = [line]
                else:
                    current_message.append(line)
        
        if current_message:
            messages.append('\n'.join(current_message))
        
        return messages

    def _extract_decisions(
        self, 
        text: str, 
        conversation_id: Optional[str], 
        context_files: Optional[List[str]]
    ) -> List[Decision]:
        """Extract decision statements from text"""
        
        decisions = []
        text_lower = text.lower()
        
        for pattern in self.decision_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                decision_text = match.group(1).strip()
                if len(decision_text) < 5:  # Skip very short matches
                    continue
                
                # Try to extract reasoning from surrounding context
                reasoning = self._extract_reasoning(text, match.start(), match.end())
                
                # Extract file references
                files = self._extract_file_references(text)
                if context_files:
                    files.extend(context_files)
                files = list(set(files))  # Deduplicate
                
                # Create decision
                decision = Decision(
                    decision=decision_text,
                    reasoning=reasoning,
                    files=files,
                    conversation_id=conversation_id,
                    tags=self._extract_tags(text, decision_text)
                )
                
                decisions.append(decision)
        
        return decisions

    def _extract_todos(
        self, 
        text: str, 
        conversation_id: Optional[str], 
        context_files: Optional[List[str]]
    ) -> List[Todo]:
        """Extract TODO items from text"""
        
        todos = []
        text_lower = text.lower()
        
        for pattern in self.todo_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                task_text = match.group(1).strip()
                if len(task_text) < 5:  # Skip very short matches
                    continue
                
                # Extract context/reasoning
                context = self._extract_reasoning(text, match.start(), match.end())
                
                # Extract file references
                files = self._extract_file_references(text)
                if context_files:
                    files.extend(context_files)
                files = list(set(files))
                
                # Determine priority from text
                priority = self._determine_priority(text, task_text)
                
                # Create TODO
                todo = Todo(
                    task=task_text,
                    context=context,
                    priority=priority,
                    files=files,
                    conversation_id=conversation_id,
                    tags=self._extract_tags(text, task_text)
                )
                
                todos.append(todo)
        
        return todos

    def _extract_rejections(
        self, 
        text: str, 
        conversation_id: Optional[str], 
        context_files: Optional[List[str]]
    ) -> List[Decision]:
        """Extract rejected approaches as decisions"""
        
        rejections = []
        text_lower = text.lower()
        
        for pattern in self.rejection_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                rejected_text = match.group(1).strip()
                if len(rejected_text) < 3:
                    continue
                
                reasoning = self._extract_reasoning(text, match.start(), match.end())
                files = self._extract_file_references(text)
                if context_files:
                    files.extend(context_files)
                files = list(set(files))
                
                # Create as decision with rejection tag
                decision = Decision(
                    decision=f"Rejected: {rejected_text}",
                    reasoning=reasoning,
                    files=files,
                    conversation_id=conversation_id,
                    tags=["rejected", "architecture"] + self._extract_tags(text, rejected_text)
                )
                
                rejections.append(decision)
        
        return rejections

    def _extract_reasoning(self, text: str, start_pos: int, end_pos: int) -> str:
        """Extract reasoning/context around a match"""
        
        # Look for sentences before and after the match
        sentences = re.split(r'[.!?]+', text)
        match_sentence = ""
        
        # Find which sentence contains the match
        char_count = 0
        for sentence in sentences:
            if char_count <= start_pos <= char_count + len(sentence):
                match_sentence = sentence.strip()
                break
            char_count += len(sentence) + 1
        
        # Look for "because", "since", "for", etc. in nearby text
        reasoning_keywords = r'\b(?:because|since|for|due to|given that|as|reason|why|benefit|advantage)\b'
        
        # Check the sentence and surrounding sentences
        full_context = text[max(0, start_pos - 200):end_pos + 200]
        reasoning_match = re.search(reasoning_keywords + r'[^.!?]*', full_context, re.IGNORECASE)
        
        if reasoning_match:
            return reasoning_match.group(0).strip()
        else:
            return match_sentence

    def _extract_file_references(self, text: str) -> List[str]:
        """Extract file paths from text"""
        
        file_patterns = [
            r'\b[\w/-]+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|go|rs|rb|php|swift|kt|scala)\b',
            r'\b[\w/-]+/[\w.-]+\b',  # Directory paths
            r'`([^`]+\.[a-zA-Z]+)`',  # Files in backticks
        ]
        
        files = []
        for pattern in file_patterns:
            matches = re.findall(pattern, text)
            files.extend(matches)
        
        # Clean up and validate
        cleaned_files = []
        for file in files:
            if isinstance(file, tuple):  # From groups in regex
                file = file[0]
            file = file.strip('`"\'')
            if len(file) > 2 and '.' in file:
                cleaned_files.append(file)
        
        return list(set(cleaned_files))

    def _extract_tags(self, text: str, content: str) -> List[str]:
        """Extract relevant tags from text and content"""
        
        tags = []
        text_lower = text.lower()
        content_lower = content.lower()
        
        # Technology tags
        tech_tags = {
            'api': ['api', 'endpoint', 'rest', 'graphql'],
            'database': ['database', 'db', 'sql', 'postgres', 'mongo'],
            'frontend': ['frontend', 'ui', 'react', 'vue', 'angular'],
            'backend': ['backend', 'server', 'express', 'fastapi', 'django'],
            'testing': ['test', 'testing', 'unit', 'integration'],
            'security': ['auth', 'security', 'permission', 'jwt', 'session'],
            'performance': ['performance', 'speed', 'fast', 'slow', 'optimize'],
            'architecture': ['architecture', 'design', 'pattern', 'structure']
        }
        
        for tag, keywords in tech_tags.items():
            if any(keyword in text_lower or keyword in content_lower for keyword in keywords):
                tags.append(tag)
        
        return tags

    def _determine_priority(self, text: str, task: str) -> str:
        """Determine priority of a task from context"""
        
        text_lower = text.lower()
        task_lower = task.lower()
        
        high_indicators = ['urgent', 'critical', 'asap', 'important', 'must', 'required', 'blocker']
        low_indicators = ['later', 'eventually', 'nice to have', 'optional', 'future']
        
        if any(indicator in text_lower or indicator in task_lower for indicator in high_indicators):
            return "high"
        elif any(indicator in text_lower or indicator in task_lower for indicator in low_indicators):
            return "low"
        else:
            return "medium"

    def _deduplicate_memories(self, memories: List[Memory]) -> List[Memory]:
        """Remove duplicate or very similar memories"""
        
        if not memories:
            return memories
        
        unique_memories = []
        seen_content = set()
        
        for memory in memories:
            # Create a normalized version for comparison
            normalized = memory.content.lower().strip()
            normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
            
            if normalized not in seen_content:
                seen_content.add(normalized)
                unique_memories.append(memory)
        
        return unique_memories