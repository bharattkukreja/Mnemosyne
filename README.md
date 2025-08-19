# Mnemosyne

A CLI tool for automatically capturing conversations with Claude/Cursor and other AI assistants.

## Features

- **Interactive Mode**: Manually capture conversations in real-time
- **Rich CLI Interface**: Beautiful terminal output with Rich library
- **Multiple Formats**: Save conversations as JSON and readable text
- **Conversation Management**: List, view, and manage saved conversations
- **Extensible**: Easy to extend for different conversation sources

## Installation

### From Source

1. Clone the repository:

```bash
git clone <repository-url>
cd Mnemosyne
```

2. Activate your virtual environment:

```bash
source mnem_venv/bin/activate  # On macOS/Linux
# or
mnem_venv\Scripts\activate     # On Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Install the package in development mode:

```bash
pip install -e .
```

## Usage

### Quick Start

Run the demo to see the tool in action:

```bash
python main.py demo
```

### Interactive Mode

Start an interactive session to manually capture conversations:

```bash
python main.py interactive
```

This will start a command-line interface where you can:

- Type `user` to add a user message
- Type `assistant` to add an assistant message
- Type `print` to view the current conversation
- Type `save` to save the conversation to file
- Type `quit` to exit

### Command Line Interface

The tool provides several commands:

#### Start a new conversation

```bash
python main.py start --title "My Conversation"
```

#### Add messages

```bash
python main.py add "Hello, can you help me?" --role user
python main.py add "Of course! What do you need help with?" --role assistant
```

#### View current conversation

```bash
python main.py print
```

#### Save conversation

```bash
python main.py save
```

#### List saved conversations

```bash
python main.py list
```

#### View a specific conversation

```bash
python main.py show 20241201_143022_My_Conversation.json
```

### Options

Most commands support these options:

- `--output-dir` or `-o`: Specify output directory (default: `conversations`)
- `--title` or `-t`: Set conversation title
- `--role` or `-r`: Specify message role (user/assistant)

## Output Format

Conversations are saved in two formats:

1. **JSON format** (`.json`): Structured data with metadata
2. **Text format** (`.txt`): Human-readable conversation

Example JSON structure:

```json
{
  "id": "conv_1701234567",
  "title": "My Conversation",
  "messages": [
    {
      "role": "user",
      "content": "Hello!",
      "timestamp": "2023-11-29T10:30:00",
      "metadata": null
    },
    {
      "role": "assistant",
      "content": "Hi there! How can I help you?",
      "timestamp": "2023-11-29T10:30:05",
      "metadata": null
    }
  ],
  "created_at": "2023-11-29T10:30:00",
  "updated_at": "2023-11-29T10:30:05",
  "source": "claude/cursor"
}
```

## Project Structure

```
Mnemosyne/
├── mnemosyne/
│   ├── __init__.py
│   ├── models.py          # Data models
│   ├── capture.py         # Core capture functionality
│   └── cli.py            # CLI interface
├── main.py               # Entry point
├── setup.py             # Package setup
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Future Enhancements

- **Automatic Capture**: Monitor browser/application logs for automatic conversation detection
- **API Integration**: Direct integration with Claude/Cursor APIs
- **Search & Filter**: Advanced search capabilities for saved conversations
- **Export Options**: Export to various formats (Markdown, PDF, etc.)
- **Tags & Categories**: Organize conversations with tags and categories
- **Backup & Sync**: Cloud backup and synchronization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI interface
- Beautiful terminal output with [Rich](https://rich.readthedocs.io/)
- Data validation with [Pydantic](https://pydantic-docs.helpmanual.io/)
