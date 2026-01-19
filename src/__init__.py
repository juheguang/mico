"""
Mico - 一个精简的 AI Agent 实现

受 OpenCode 项目启发，用于学习 AI Agent 的核心概念。
"""

from .models import (
    Session, Message, UserMessage, AssistantMessage,
    TextPart, ToolPart, ReasoningPart, ToolCall, ToolState,
    AgentConfig, AgentMode,
    PermissionAction, PermissionRule,
    generate_id, generate_session_id,
)
from .session import (
    SessionManager,
    create_user_message, create_assistant_message,
    add_text_part, add_tool_part, update_tool_part,
    messages_to_openai_format,
)
from .permission import (
    PermissionManager, PermissionDeniedError, PermissionRejectedError,
    create_default_permission_manager,
)
from .agent import AgentManager, create_build_agent, create_plan_agent
from .logger import get_logger, setup_logger
from .loop import AgentLoop, run_agent

from .llm import (
    BaseLLMProvider, StreamChunk, LLMResponse, LLMConfig,
    OpenAIProvider, AnthropicProvider, DeepSeekProvider,
    create_provider, parse_model, list_providers, SUPPORTED_PROVIDERS,
)
from .errors import (
    AgentError, LLMError, LLMTimeoutError, LLMNetworkError,
    LLMRateLimitError, LLMAPIError, ToolError, ToolTimeoutError,
    RetryConfig, ErrorHandler,
)
from .tools import (
    BaseTool, ToolContext, ToolResult, ToolRegistry,
    BashTool, ReadTool, EditTool, GlobTool, ListTool,
    create_default_registry,
)
from .ui import console, EditStreamPreview


__version__ = "0.1.0"

__all__ = [
    # Models
    "Session", "Message", "UserMessage", "AssistantMessage",
    "TextPart", "ToolPart", "ReasoningPart", "ToolCall", "ToolState",
    "AgentConfig", "AgentMode",
    "PermissionAction", "PermissionRule",
    "generate_id", "generate_session_id",

    # Session
    "SessionManager",
    "create_user_message", "create_assistant_message",
    "add_text_part", "add_tool_part", "update_tool_part",
    "messages_to_openai_format",

    # Permission
    "PermissionManager", "PermissionDeniedError", "PermissionRejectedError",
    "create_default_permission_manager",

    # Agent
    "AgentManager", "create_build_agent", "create_plan_agent",

    # Logger
    "get_logger", "setup_logger",

    # Loop
    "AgentLoop", "run_agent",

    # LLM
    "BaseLLMProvider", "StreamChunk", "LLMResponse", "LLMConfig",
    "OpenAIProvider", "AnthropicProvider", "DeepSeekProvider",
    "create_provider", "parse_model", "list_providers", "SUPPORTED_PROVIDERS",

    # Errors
    "AgentError", "LLMError", "LLMTimeoutError", "LLMNetworkError",
    "LLMRateLimitError", "LLMAPIError", "ToolError", "ToolTimeoutError",
    "RetryConfig", "ErrorHandler",

    # Tools
    "BaseTool", "ToolContext", "ToolResult", "ToolRegistry",
    "BashTool", "ReadTool", "EditTool", "GlobTool", "ListTool",
    "create_default_registry",

    # UI
    "console", "EditStreamPreview",
]
