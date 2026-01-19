"""
工具系统基类和通用组件
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from ..permission import PermissionManager


class ToolContext:
    """工具执行上下文"""

    def __init__(
        self,
        session_id: str,
        message_id: str,
        agent: str,
        permission_manager: "PermissionManager",
        working_dir: str = ".",
    ):
        self.session_id = session_id
        self.message_id = message_id
        self.agent = agent
        self.permission = permission_manager
        self.working_dir = Path(working_dir).resolve()
        self.aborted = False
        # 预先通过的权限（避免重复提示）
        self._preapproved: dict[str, set[str]] = {}

    def preapprove(self, permission: str, patterns: list[str]) -> None:
        """标记已通过的权限，避免重复提示"""
        if permission not in self._preapproved:
            self._preapproved[permission] = set()
        for pattern in patterns:
            self._preapproved[permission].add(pattern)

    async def ask_permission(
        self,
        permission: str,
        patterns: list[str],
        metadata: dict = None
    ):
        """请求权限"""
        # 如果已经预先通过，则跳过询问
        if permission in self._preapproved:
            remaining = [p for p in patterns if p not in self._preapproved[permission]]
            if not remaining:
                return
            patterns = remaining
        await self.permission.check(permission, patterns, metadata)


class ToolResult(BaseModel):
    """工具执行结果"""
    output: str
    title: str = ""
    metadata: dict[str, Any] = {}
    error: Optional[str] = None


class BaseTool(ABC):
    """工具基类"""

    name: str
    description: str

    @abstractmethod
    def get_parameters_schema(self) -> dict:
        """返回参数的 JSON Schema"""
        pass

    @abstractmethod
    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        """执行工具"""
        pass

    def to_openai_tool(self) -> dict:
        """转换为 OpenAI 工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema()
            }
        }


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """列出所有工具"""
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict]:
        """转换为 OpenAI 工具列表"""
        return [tool.to_openai_tool() for tool in self._tools.values()]
