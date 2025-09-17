"""MCP tools for knowledge graph exploration"""

import logging
from typing import Any, Sequence, List
from mcp import types

from config import Config
from memory.storage import MemoryStorage

logger = logging.getLogger(__name__)


class GraphTools:
    """MCP tools for exploring the knowledge graph"""
    
    def __init__(self, config: Config):
        self.config = config
        self.storage = MemoryStorage(config)
    
    async def explore_relationships(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Explore relationships around a specific memory"""
        try:
            memory_id = arguments["memory_id"]
            max_depth = arguments.get("max_depth", 2)
            
            # Get the base memory
            base_memory = self.storage.get_memory(memory_id)
            if not base_memory:
                return [
                    types.TextContent(
                        type="text",
                        text=f"❌ Memory with ID {memory_id} not found"
                    )
                ]
            
            # Find related memories
            related_memories = self.storage.get_related_memories(memory_id, max_depth)
            
            if not related_memories:
                return [
                    types.TextContent(
                        type="text",
                        text=f"🔗 **Relationship Explorer**\n\n"
                             f"**Base Memory:** {base_memory.content}\n"
                             f"**Type:** {base_memory.type}\n\n"
                             f"No related memories found in the knowledge graph."
                    )
                ]
            
            # Format response
            response_lines = [
                "🔗 **Knowledge Graph Relationships**",
                "",
                f"**Base Memory:** {base_memory.content}",
                f"**Type:** {base_memory.type.title()}",
                f"**Created:** {base_memory.timestamp.strftime('%Y-%m-%d %H:%M')}",
                "",
                f"**Found {len(related_memories)} related memories:**",
                ""
            ]
            
            # Group by depth
            by_depth = {}
            for memory in related_memories:
                depth = memory["depth"]
                if depth not in by_depth:
                    by_depth[depth] = []
                by_depth[depth].append(memory)
            
            for depth in sorted(by_depth.keys()):
                memories = by_depth[depth]
                
                if depth == 1:
                    response_lines.append("### 🔗 Directly Connected")
                elif depth == 2:
                    response_lines.append("### 🔗🔗 2nd Degree Connections")
                else:
                    response_lines.append(f"### {'🔗' * depth} {depth}-Degree Connections")
                
                response_lines.append("")
                
                for i, memory in enumerate(memories, 1):
                    # Determine emoji based on type
                    type_emoji = {
                        "decision": "🏗️",
                        "todo": "📋", 
                        "bug_fix": "🐛"
                    }.get(memory["type"], "💭")
                    
                    response_lines.extend([
                        f"**{i}. {type_emoji} {memory['content']}**",
                        f"*Path:* {' → '.join(memory['relationship_path'])}",
                        f"*Created:* {memory['timestamp'][:10]}",
                        ""
                    ])
            
            return [
                types.TextContent(
                    type="text",
                    text="\n".join(response_lines)
                )
            ]
            
        except Exception as e:
            logger.error(f"Failed to explore relationships: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to explore relationships: {str(e)}"
                )
            ]
    
    async def analyze_decision_impact(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Analyze the impact and influence of a specific decision"""
        try:
            decision_id = arguments["decision_id"]
            
            # Get decision details
            decision = self.storage.get_memory(decision_id)
            if not decision or decision.type != "decision":
                return [
                    types.TextContent(
                        type="text",
                        text=f"❌ Decision with ID {decision_id} not found"
                    )
                ]
            
            # Analyze impact
            impact = self.storage.analyze_decision_impact(decision_id)
            
            if not impact:
                return [
                    types.TextContent(
                        type="text",
                        text=f"📊 **Decision Impact Analysis**\n\n"
                             f"**Decision:** {decision.content}\n"
                             f"**Made:** {decision.timestamp.strftime('%Y-%m-%d %H:%M')}\n\n"
                             f"No impact data available (Neo4j may not be connected)."
                    )
                ]
            
            # Format response
            response_lines = [
                "📊 **Decision Impact Analysis**",
                "",
                f"**Decision:** {impact.get('decision_content', decision.content)}",
                f"**Made:** {decision.timestamp.strftime('%Y-%m-%d %H:%M')}",
                f"**Reasoning:** {decision.reasoning}",
                ""
            ]
            
            # Affected files
            affected_files = impact.get("affected_files", [])
            if affected_files:
                response_lines.extend([
                    "### 📁 Affected Files",
                    ""
                ])
                for file in affected_files:
                    response_lines.append(f"• `{file}`")
                response_lines.append("")
            
            # Subsequent changes
            subsequent_changes = impact.get("subsequent_changes", [])
            if subsequent_changes:
                response_lines.extend([
                    "### 🔄 Subsequent Changes",
                    ""
                ])
                for change in subsequent_changes:
                    change_emoji = "🏗️" if change["type"] == "decision" else "📋"
                    response_lines.extend([
                        f"**{change_emoji} {change['content']}**",
                        f"*{change['type'].title()} • {change['timestamp'][:10]}*",
                        ""
                    ])
            
            # Related decisions
            related_decisions = impact.get("related_decisions", [])
            if related_decisions:
                response_lines.extend([
                    "### 🔗 Related Decisions",
                    ""
                ])
                for related in related_decisions:
                    response_lines.extend([
                        f"**🏗️ {related['content']}**",
                        f"*{related['timestamp'][:10]}*",
                        ""
                    ])
            
            # Summary
            response_lines.extend([
                "---",
                f"**Impact Summary:**",
                f"• Files affected: {len(affected_files)}",
                f"• Subsequent changes: {len(subsequent_changes)}",
                f"• Related decisions: {len(related_decisions)}"
            ])
            
            return [
                types.TextContent(
                    type="text",
                    text="\n".join(response_lines)
                )
            ]
            
        except Exception as e:
            logger.error(f"Failed to analyze decision impact: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to analyze decision impact: {str(e)}"
                )
            ]
    
    async def discover_patterns(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Discover knowledge patterns in the graph"""
        try:
            # Get knowledge patterns
            patterns = self.storage.discover_knowledge_patterns()
            
            if not patterns:
                return [
                    types.TextContent(
                        type="text",
                        text="🔍 **Knowledge Pattern Discovery**\n\n"
                             "No patterns found (Neo4j may not be connected or no data available)."
                    )
                ]
            
            # Format response
            response_lines = [
                "🔍 **Knowledge Pattern Discovery**",
                "",
                "Analyzing patterns in your codebase memory...",
                ""
            ]
            
            # Most active files
            most_active_files = patterns.get("most_active_files", [])
            if most_active_files:
                response_lines.extend([
                    "### 📁 Most Discussed Files",
                    ""
                ])
                for file_data in most_active_files[:5]:  # Top 5
                    file_path = file_data["file"]
                    memory_count = file_data["memories"]
                    bar = "█" * min(memory_count, 20)  # Visual bar
                    response_lines.append(f"`{file_path}` {bar} {memory_count} memories")
                response_lines.append("")
            
            # Popular tags
            popular_tags = patterns.get("popular_tags", [])
            if popular_tags:
                response_lines.extend([
                    "### 🏷️ Most Used Tags",
                    ""
                ])
                for tag_data in popular_tags[:8]:  # Top 8
                    tag_name = tag_data["tag"]
                    usage_count = tag_data["usage"]
                    response_lines.append(f"**{tag_name}** ({usage_count} uses)")
                response_lines.append("")
            
            # Decision chains
            decision_chains = patterns.get("decision_chains", [])
            if decision_chains:
                response_lines.extend([
                    "### 🔗 Decision Chain Analysis",
                    ""
                ])
                for chain_data in decision_chains:
                    length = chain_data["length"]
                    count = chain_data["count"]
                    response_lines.append(f"• {count} chains of length {length}")
                response_lines.append("")
            
            # Insights
            response_lines.extend([
                "### 💡 Insights",
                ""
            ])
            
            if most_active_files:
                top_file = most_active_files[0]["file"]
                top_count = most_active_files[0]["memories"]
                response_lines.append(f"• `{top_file}` is your most discussed file ({top_count} memories)")
            
            if popular_tags:
                top_tag = popular_tags[0]["tag"]
                response_lines.append(f"• **{top_tag}** is your most common topic")
            
            total_chains = sum(c["count"] for c in decision_chains)
            if total_chains > 0:
                response_lines.append(f"• {total_chains} decision chains show architectural evolution")
            
            return [
                types.TextContent(
                    type="text",
                    text="\n".join(response_lines)
                )
            ]
            
        except Exception as e:
            logger.error(f"Failed to discover patterns: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to discover patterns: {str(e)}"
                )
            ]
    
    async def trace_file_evolution(self, arguments: dict[str, Any]) -> Sequence[types.TextContent]:
        """Trace the evolution of decisions and discussions for a file"""
        try:
            file_path = arguments["filepath"]
            
            # Get file evolution from graph
            evolution = self.storage.get_file_evolution(file_path)
            
            if not evolution:
                return [
                    types.TextContent(
                        type="text",
                        text=f"📈 **File Evolution: {file_path}**\n\n"
                             f"No evolution data found.\n"
                             f"This file hasn't been discussed in tracked conversations, or Neo4j is not connected."
                    )
                ]
            
            # Format chronological evolution
            response_lines = [
                f"📈 **File Evolution: {file_path}**",
                "",
                f"Chronological history of {len(evolution)} memories:",
                ""
            ]
            
            for i, memory in enumerate(evolution, 1):
                # Format timestamp
                timestamp = memory["timestamp"]
                if isinstance(timestamp, str):
                    date_str = timestamp[:10]
                else:
                    date_str = timestamp.strftime('%Y-%m-%d')
                
                # Determine emoji and format
                type_emoji = {
                    "decision": "🏗️",
                    "todo": "📋",
                    "bug_fix": "🐛"
                }.get(memory["type"], "💭")
                
                response_lines.extend([
                    f"### {i}. {type_emoji} {date_str}",
                    f"**{memory['type'].title()}:** {memory['content']}",
                ])
                
                if memory.get("reasoning"):
                    response_lines.append(f"*Reasoning:* {memory['reasoning']}")
                
                if memory.get("conversation_id"):
                    response_lines.append(f"*Conversation:* {memory['conversation_id']}")
                
                response_lines.append("")
            
            # Add summary
            decision_count = sum(1 for m in evolution if m["type"] == "decision")
            todo_count = sum(1 for m in evolution if m["type"] == "todo")
            
            response_lines.extend([
                "---",
                "**Evolution Summary:**",
                f"• {decision_count} architectural decisions",
                f"• {todo_count} tasks/TODOs",
                f"• Tracked over {len(set(m['timestamp'][:7] for m in evolution))} months"
            ])
            
            return [
                types.TextContent(
                    type="text",
                    text="\n".join(response_lines)
                )
            ]
            
        except Exception as e:
            logger.error(f"Failed to trace file evolution: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to trace file evolution: {str(e)}"
                )
            ]