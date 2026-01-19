<div align="center">
  <img src="images/mico.png" alt="Mico Logo" width="300">
</div>

> A lightweight AI coding assistant inspired by [OpenCode](https://github.com/anomalyco/opencode)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Mico is a simplified AI coding assistant that brings the core architecture of OpenCode to Python. It provides an interactive terminal interface for AI-powered code generation, editing, and analysis with support for multiple LLM providers.

## ✨ Features

- **Multi-Provider Support**: Works with OpenAI, Anthropic, and DeepSeek APIs
- **Interactive Terminal UI**: Beautiful Rich-based interface with real-time streaming
- **Multiple Agents**: Specialized agents for different tasks (build, plan, etc.)
- **Tool System**: Extensible tool ecosystem (bash, read, edit, glob, list, ask_user)
- **Permission System**: Fine-grained permission control with allow/deny/ask rules
- **Session Management**: Persistent conversation history with easy session switching
- **Streaming Preview**: Real-time code preview during file editing
- **Structured Logging**: Comprehensive logging for debugging and auditing
- **Working Directory Support**: Work with any project directory (absolute or relative paths)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mico

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# LLM Provider API Keys (at least one required)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
DEEPSEEK_API_KEY=sk-xxx

# Default Settings
MICO_MODEL=deepseek/deepseek-chat
MICO_DEFAULT_AGENT=build
MICO_WORKING_DIR=.
MICO_USERNAME=yourname
```

### Run

```bash
# Interactive mode
python main.py

# Single execution
python main.py "Create a Python hello world program"

# Specify model
python main.py -m anthropic/claude-sonnet-4-20250514 "Analyze this project"

# Specify working directory
python main.py -d /path/to/project "Analyze this project"
python main.py -d ../other-project "Analyze this project"

# List supported providers
python main.py --list-providers
```

## 📖 Usage

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/a` | Cycle through available agents |
| `/model [id]` | Switch to a different model |
| `/cd <path>` | Change working directory |
| `/clear` | Clear current conversation |
| `/sessions` | List all sessions |
| `/load <id>` | Load a previous session |
| `/delete <id>` | Delete a session |
| `/info` | Show current session information |
| `/tokens` | Show token usage statistics |
| `/status` | Display status bar |
| `/quit` | Exit the application |

### Agents

Mico supports multiple specialized agents:

| Agent | Mode | Description |
|-------|------|-------------|
| `build` | Primary | Full-featured agent for code generation and editing |
| `plan` | Primary | Read-only agent for analysis and planning |

**Example: Using the plan agent**

```bash
python main.py -a plan "What is the architecture of this project?"
```

The plan agent will:
- Ask clarifying questions using `ask_user` tool
- Use read-only tools (`read`, `glob`, `list`) for inspection
- Create a detailed plan document (`PLAN_<topic>.md`) after clarification

### Built-in Tools

| Tool | Description |
|------|-------------|
| `bash` | Execute shell commands |
| `read` | Read file contents |
| `edit` | Edit files (search and replace) |
| `glob` | Search files using wildcard patterns |
| `list` | List directory contents |
| `ask_user` | Ask structured questions to the user |

## 🛡️ Permission System

Mico includes a fine-grained permission system to control agent actions:

- **allow**: Automatically allow the action
- **deny**: Automatically deny the action
- **ask**: Prompt the user for permission

**Example permission rules:**

```python
PermissionRule(permission="bash", pattern="rm *", action=PermissionAction.ASK)
PermissionRule(permission="edit", pattern="*.env", action=PermissionAction.ASK)
PermissionRule(permission="read", pattern="*", action=PermissionAction.ALLOW)
```

## 📁 Project Structure

```
mico/
├── main.py                  # CLI entry point
├── src/                     # Core source code
│   ├── __init__.py          # Package exports
│   ├── models.py            # Data models (Session, Message, Agent, etc.)
│   ├── session.py           # Session management
│   ├── permission.py        # Permission system
│   ├── agent.py             # Agent configuration and management
│   ├── logger.py            # Logging system
│   ├── loop.py              # Core agent execution loop
│   ├── errors.py            # Error handling and exceptions
│   ├── llm/                 # LLM provider modules
│   │   ├── __init__.py      # Provider factory
│   │   ├── base.py          # Base provider class
│   │   ├── openai.py        # OpenAI provider
│   │   ├── anthropic.py     # Anthropic provider
│   │   └── deepseek.py      # DeepSeek provider
│   ├── tools/               # Tool modules
│   │   ├── __init__.py      # Tool registry
│   │   ├── base.py          # Base tool class
│   │   ├── bash.py          # Bash command tool
│   │   ├── read.py          # File reading tool
│   │   ├── edit.py          # File editing tool
│   │   ├── glob.py          # File search tool
│   │   ├── list.py          # Directory listing tool
│   │   └── ask_user.py      # User interaction tool
│   └── ui/                  # UI components
│       ├── __init__.py      # UI exports
│       ├── console.py       # Rich console setup
│       ├── message.py       # Message formatting
│       ├── preview.py       # Streaming edit preview
│       ├── startup.py       # Startup screen and animations
│       └── tool_display.py  # Tool output formatting
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
└── README.md                # This file
```

## 🎨 UI Features

### Streaming Edit Preview

When the agent creates or edits files, Mico displays a real-time preview showing the last 5 lines being written:

```
┌─ Editing: hello.py (12 lines, 256 chars) ─
│ ... (7 lines omitted) ...
│    8 │     return "Hello, World!"
│    9 │
│   10 │ if __name__ == "__main__":
│   11 │     main()
│   12 │ ▌
└─────────────────────────────────────────
```

### Status Bar

The status bar displays:
- Current model
- Active agent
- Working directory
- Username (if configured)
- Token usage (optional)

### Rich Terminal Output

- Syntax-highlighted code
- Formatted directory trees
- Color-coded tool outputs
- Progress indicators and loading animations

## 📝 Logging

Mico automatically logs all interactions for debugging and auditing.

### Log Location

Logs are saved in `.mico/logs/` within the working directory, organized by date:

```
.mico/logs/
├── 2026-01-16.log
├── 2026-01-17.log
└── ...
```

### Log Events

| Event Type | Description |
|------------|-------------|
| `SESSION_START` | Session initialization (agent, model, working directory) |
| `SESSION_END` | Session completion (total steps, token usage) |
| `USER_INPUT` | User messages |
| `LLM_REQUEST` | LLM API requests (message count, tool count) |
| `LLM_RESPONSE` | LLM API responses (finish reason, tokens, duration) |
| `TOOL_CALL` | Tool invocations (parameters) |
| `TOOL_RESULT` | Tool execution results (success/failure, duration) |
| `PERMISSION_*` | Permission requests and decisions |

## 🏗️ Architecture

### Core Execution Loop

```
User Input
    ↓
Create UserMessage
    ↓
┌─────────────────────────────┐
│  while step < max_steps:    │
│    ↓                        │
│  Build message history      │
│    ↓                        │
│  Call LLM (stream)          │
│    ↓                        │
│  Process response:          │
│    - Text → Add TextPart    │
│    - Tool → Execute & update│
│    ↓                        │
│  Check termination:         │
│    - stop → Exit loop       │
│    - tool_calls → Continue  │
│    - doom loop → Ask user   │
└─────────────────────────────┘
    ↓
Return AssistantMessage
```

### Key Design Decisions

1. **Main Loop**: Uses `while` loop instead of recursion for better state control and interrupt handling
2. **Streaming**: Real-time processing of LLM responses, supporting mixed text and tool calls
3. **Permission System**: Fine-grained control with wildcard support and decision memory
4. **Doom Loop Detection**: Prevents agents from getting stuck in infinite loops
5. **Tool Abstraction**: Unified tool interface for easy extensibility
6. **Modular Design**: Clear directory structure with well-defined module responsibilities

## 🔌 Supported Providers

You can also adapt more model providers by following the code in `./src/llm/deepseek.py`.

| Provider | Models | API Key Env Var |
|----------|--------|----------------|
| OpenAI | `gpt-4o`, `gpt-4-turbo`, etc. | `OPENAI_API_KEY` |
| Anthropic | `claude-sonnet-4-20250514`, `claude-3-5-sonnet-20241022`, etc. | `ANTHROPIC_API_KEY` |
| DeepSeek | `deepseek-chat`, `deepseek-coder`, `deepseek-reasoner` | `DEEPSEEK_API_KEY` |

## 📋 Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Inspired by [OpenCode](https://github.com/anomalyco/opencode)
- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output


## 📚 Additional Resources

- [OpenCode Documentation](https://github.com/anomalyco/opencode)
- [Rich Documentation](https://rich.readthedocs.io/)

---

**Note**: This is a simplified implementation focused on core functionality. For production use, consider additional features like:
- Enhanced error recovery
- More sophisticated doom loop detection
- Additional tool integrations
- Performance optimizations
