"""
工具模块 - 提供 Agent 可用的各种工具
"""

from .base import BaseTool, ToolContext, ToolResult, ToolRegistry
from .bash import BashTool
from .read import ReadTool
from .edit import EditTool
from .glob import GlobTool
from .list import ListTool
from .ask_user import AskUserTool


def create_default_registry() -> ToolRegistry:
    """创建默认工具注册表"""
    registry = ToolRegistry()
    registry.register(BashTool())
    registry.register(ReadTool())
    registry.register(EditTool())
    registry.register(GlobTool())
    registry.register(ListTool())
    registry.register(AskUserTool())
    return registry


__all__ = [
    "BaseTool",
    "ToolContext",
    "ToolResult",
    "ToolRegistry",
    "BashTool",
    "ReadTool",
    "EditTool",
    "GlobTool",
    "ListTool",
    "AskUserTool",
    "create_default_registry",
]
