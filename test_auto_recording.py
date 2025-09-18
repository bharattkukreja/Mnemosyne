#!/usr/bin/env python3
"""Simple demonstration of automatic recording functionality"""

import asyncio
import time
from pathlib import Path

from memory.auto_trigger import AutoTrigger, MCPConversationIntegration
from config import load_config, ensure_directories

async def demo_auto_recording():
    """Demonstrate automatic recording of code changes with conversation context"""

    print("🚀 Mnemosyne Auto-Recording Demo")
    print("=" * 50)

    # Initialize
    config = load_config("config.yaml")
    ensure_directories(config)

    auto_trigger = AutoTrigger(config)
    integration = MCPConversationIntegration(auto_trigger)

    # Simulate a conversation
    print("\n💬 Simulating conversation...")
    integration.on_user_message("I need to create a utility function for data processing")
    time.sleep(0.1)

    integration.on_assistant_message("I'll create a data utility module for you with processing functions")
    time.sleep(0.1)

    integration.on_user_message("Make sure it handles both JSON and CSV formats")
    time.sleep(0.1)

    integration.on_assistant_message("Perfect! I'll add support for both JSON and CSV processing")
    time.sleep(0.1)

    print(f"📝 Recorded {len(auto_trigger.conversation_tracker.messages)} conversation messages")

    # Start watching (without watchdog this won't actually watch files)
    print("\n🔍 Starting file system watching...")
    await auto_trigger.start_watching()

    # Simulate file creation
    print("\n📁 Simulating file creation...")
    test_file = Path("data_utils.py")

    # Create the file
    with open(test_file, 'w') as f:
        f.write('''#!/usr/bin/env python3
"""Data processing utilities"""

import json
import csv
from typing import Dict, List, Any

def process_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process JSON data"""
    # Implementation here
    return data

def process_csv(filepath: str) -> List[Dict[str, Any]]:
    """Process CSV file"""
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)
''')

    print(f"✅ Created test file: {test_file}")

    # Manually trigger the file change handler
    from memory.auto_trigger import FileChange
    from datetime import datetime

    change = FileChange(
        file_path=str(test_file),
        change_type="created",
        timestamp=datetime.now()
    )

    print("\n🎯 Triggering automatic context association...")
    await auto_trigger.handle_file_change(change)

    # Check recent messages
    print("\n📊 Recent conversation context:")
    recent_messages = auto_trigger.conversation_tracker.get_recent_messages(count=5)
    for i, msg in enumerate(recent_messages, 1):
        print(f"  {i}. {msg[:80]}...")

    # Cleanup
    print(f"\n🧹 Cleaning up test file...")
    test_file.unlink()
    auto_trigger.stop_watching()

    print("\n✅ Auto-recording demonstration complete!")
    print("\nNow when you call `start_auto_recording()` via MCP, this conversation would be automatically recorded!")

if __name__ == "__main__":
    asyncio.run(demo_auto_recording())