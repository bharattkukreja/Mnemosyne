#!/usr/bin/env python3
"""
Mnemosyne CLI - Command line interface for memory layer MCP server
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from config import ensure_directories, load_config


def get_cursor_config_paths() -> list[Path]:
    """Get all possible paths to Cursor/Claude MCP configuration files"""

    paths = []

    # Cursor MCP config (primary for Cursor)
    paths.append(Path.home() / ".cursor" / "mcp.json")

    # Claude Desktop config (standard location)
    if sys.platform == "darwin":  # macOS
        paths.append(
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    elif sys.platform == "win32":  # Windows
        paths.append(Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json")
    else:  # Linux
        paths.append(Path.home() / ".config" / "Claude" / "claude_desktop_config.json")

    # Cursor Cline MCP settings
    if sys.platform == "darwin":  # macOS
        paths.append(
            Path.home()
            / "Library"
            / "Application Support"
            / "Cursor"
            / "User"
            / "globalStorage"
            / "rooveterinaryinc.roo-cline"
            / "settings"
            / "cline_mcp_settings.json"
        )
    elif sys.platform == "win32":  # Windows
        paths.append(
            Path.home()
            / "AppData"
            / "Roaming"
            / "Cursor"
            / "User"
            / "globalStorage"
            / "rooveterinaryinc.roo-cline"
            / "settings"
            / "cline_mcp_settings.json"
        )
    else:  # Linux
        paths.append(
            Path.home()
            / ".config"
            / "Cursor"
            / "User"
            / "globalStorage"
            / "rooveterinaryinc.roo-cline"
            / "settings"
            / "cline_mcp_settings.json"
        )

    return paths


def get_cursor_config_path() -> Path:
    """Get the primary path to use for Cursor MCP configuration (backward compatibility)"""
    return get_cursor_config_paths()[0]  # Prefer .cursor/mcp.json


def get_mnemosyne_server_path() -> str:
    """Get the path to the Mnemosyne server script"""
    return str(Path(__file__).parent / "server.py")


def init_config():
    """Initialize Mnemosyne configuration"""
    print("🔧 Initializing Mnemosyne configuration...")

    try:
        config = load_config()
        ensure_directories(config)
        print("✅ Configuration initialized successfully")
        print(f"📁 Storage path: {config.storage.vector_db_path}")
        print(f"📝 Logs path: {config.logging.path}")

        # Test connections
        print("\n🧪 Testing connections...")

        # Test Neo4j
        try:
            from memory.graph import KnowledgeGraph

            kg = KnowledgeGraph(config)
            if kg.driver:
                print("✅ Neo4j: Connected")
                kg.close()
            else:
                print("⚠️  Neo4j: Not available (optional)")
        except Exception as e:
            print(f"⚠️  Neo4j: Not available ({e})")

        # Test embeddings
        try:
            from memory.embeddings import EmbeddingGenerator

            embedder = EmbeddingGenerator(config)
            if embedder.embedding_type == "sentence_transformers":
                print("✅ Embeddings: sentence-transformers available")
            else:
                print(
                    "⚠️  Embeddings: Using dummy embeddings (install sentence-transformers for better performance)"
                )
        except Exception as e:
            print(f"⚠️  Embeddings: Error ({e})")

        print("\n🚀 Mnemosyne is ready!")

    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        sys.exit(1)


def configure_cursor():
    """Configure Cursor to use Mnemosyne MCP server"""
    print("🔧 Configuring Cursor for Mnemosyne integration...")

    cursor_config_path = get_cursor_config_path()  # Use Claude Desktop config as primary
    server_path = get_mnemosyne_server_path()

    # Get full Python path
    python_path = sys.executable

    # Create the MCP configuration
    mcp_config = {"mcpServers": {"mnemosyne": {"command": python_path, "args": [server_path]}}}

    # Ensure the directory exists
    cursor_config_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing config if it exists
    existing_config = {}
    if cursor_config_path.exists():
        try:
            with open(cursor_config_path, "r") as f:
                existing_config = json.load(f)
        except Exception as e:
            print(f"⚠️  Could not read existing Cursor config: {e}")

    # Merge configurations
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}

    existing_config["mcpServers"]["mnemosyne"] = mcp_config["mcpServers"]["mnemosyne"]

    # Write the updated configuration
    try:
        with open(cursor_config_path, "w") as f:
            json.dump(existing_config, f, indent=2)

        print("✅ Cursor configuration updated successfully")
        print(f"📁 Config file: {cursor_config_path}")
        print("\n🔄 Please restart Cursor to apply the changes")
        print("\n💡 To test the integration:")
        print("   1. Open a project in Cursor")
        print("   2. Start a chat with Claude")
        print("   3. Try: 'store_decision' or 'search_memory' tools")

    except Exception as e:
        print(f"❌ Failed to update Cursor configuration: {e}")
        print(f"\n📝 Manual configuration required:")
        print(f"   Add this to {cursor_config_path}:")
        print(json.dumps(mcp_config, indent=2))
        sys.exit(1)


def start_server():
    """Start the Mnemosyne MCP server"""
    print("🚀 Starting Mnemosyne MCP server...")

    try:
        # Ensure configuration is valid
        config = load_config()
        ensure_directories(config)

        # Start the server
        server_path = get_mnemosyne_server_path()
        subprocess.run([sys.executable, server_path], check=True)

    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)


def check_status():
    """Check the status of Mnemosyne installation and configuration"""
    print("🔍 Checking Mnemosyne status...\n")

    # Check configuration
    try:
        config = load_config()
        print("✅ Configuration: Valid")
    except Exception as e:
        print(f"❌ Configuration: Invalid ({e})")
        return

    # Check storage directories
    storage_dir = Path(config.storage.vector_db_path).parent
    if storage_dir.exists():
        print(f"✅ Storage directory: {storage_dir}")
    else:
        print(f"❌ Storage directory: Missing ({storage_dir})")

    # Check Cursor configuration
    configured = False
    for config_path in get_cursor_config_paths():
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    cursor_config = json.load(f)

                if "mcpServers" in cursor_config and "mnemosyne" in cursor_config["mcpServers"]:
                    print(f"✅ Cursor integration: Configured ({config_path.name})")
                    configured = True
                    break
            except Exception as e:
                print(f"❌ Error reading {config_path.name}: {e}")

    if not configured:
        print("⚠️  Cursor integration: Not configured in any location")

    # Check dependencies
    print("\n📦 Dependencies:")

    dependencies = [
        ("mcp", "MCP Protocol"),
        ("chromadb", "Vector Database"),
        ("sentence_transformers", "Embeddings"),
        ("neo4j", "Knowledge Graph"),
        ("pyyaml", "Configuration"),
    ]

    for module, description in dependencies:
        try:
            __import__(module)
            print(f"   ✅ {description}: Available")
        except ImportError:
            print(f"   ❌ {description}: Missing (pip install {module})")

    # Check for stored memories
    try:
        from memory.storage import MemoryStorage

        storage = MemoryStorage(config)

        if storage.storage_type == "file":
            memories_file = (
                Path(config.storage.vector_db_path).parent / "file_storage" / "memories.jsonl"
            )
            if memories_file.exists():
                with open(memories_file, "r") as f:
                    memory_count = sum(1 for _ in f)
                print(f"\n💾 Stored memories: {memory_count}")
            else:
                print("\n💾 Stored memories: 0 (no memories file)")
        else:
            print(f"\n💾 Storage backend: {storage.storage_type}")

    except Exception as e:
        print(f"\n❌ Storage check failed: {e}")


def uninstall():
    """Remove Mnemosyne configuration from Cursor"""
    print("🗑️  Removing Mnemosyne from Cursor configuration...")

    cursor_config_path = get_cursor_config_path()

    if not cursor_config_path.exists():
        print("⚠️  Cursor configuration file not found - nothing to remove")
        return

    try:
        with open(cursor_config_path, "r") as f:
            config = json.load(f)

        if "mcpServers" in config and "mnemosyne" in config["mcpServers"]:
            del config["mcpServers"]["mnemosyne"]

            with open(cursor_config_path, "w") as f:
                json.dump(config, f, indent=2)

            print("✅ Mnemosyne removed from Cursor configuration")
            print("🔄 Please restart Cursor to apply the changes")
        else:
            print("⚠️  Mnemosyne not found in Cursor configuration")

    except Exception as e:
        print(f"❌ Failed to remove configuration: {e}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Mnemosyne - Memory Layer MCP Server for AI Coding Sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mnemosyne init                 # Initialize configuration
  mnemosyne configure-cursor     # Configure Cursor integration
  mnemosyne start               # Start the MCP server
  mnemosyne status              # Check installation status
  mnemosyne uninstall           # Remove from Cursor
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    subparsers.add_parser("init", help="Initialize Mnemosyne configuration")

    # Configure Cursor command
    subparsers.add_parser("configure-cursor", help="Configure Cursor to use Mnemosyne")

    # Start server command
    subparsers.add_parser("start", help="Start the Mnemosyne MCP server")

    # Status command
    subparsers.add_parser("status", help="Check Mnemosyne status and configuration")

    # Uninstall command
    subparsers.add_parser("uninstall", help="Remove Mnemosyne from Cursor configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    print("🧠 Mnemosyne - Memory Layer MCP Server")
    print("=" * 50)

    if args.command == "init":
        init_config()
    elif args.command == "configure-cursor":
        configure_cursor()
    elif args.command == "start":
        start_server()
    elif args.command == "status":
        check_status()
    elif args.command == "uninstall":
        uninstall()


if __name__ == "__main__":
    main()
