"""
数据模型定义 - 对应 OpenCode 的 message-v2.ts 和 agent.ts
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
import ulid
import secrets
import string


def generate_id(prefix: str = "") -> str:
    """生成 ULID 格式的 ID"""
    return f"{prefix}_{ulid.new().str}" if prefix else ulid.new().str


# ============ Permission Models ============

class PermissionAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionRule(BaseModel):
    """权限规则"""
    permission: str  # 权限名，如 "edit", "bash", "*"
    pattern: str     # 匹配模式，如 "*.env", "*"
    action: PermissionAction


# ============ Tool Models ============

class ToolState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class ToolCall(BaseModel):
    """工具调用记录"""
    id: str = Field(default_factory=lambda: generate_id("call"))
    tool_name: str
    input: dict[str, Any]
    state: ToolState = ToolState.PENDING
    output: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# ============ Message Models ============

class TextPart(BaseModel):
    """文本部分"""
    type: Literal["text"] = "text"
    text: str
    synthetic: bool = False  # 是否为系统生成


class ToolPart(BaseModel):
    """工具调用部分"""
    type: Literal["tool"] = "tool"
    tool_call: ToolCall


class ReasoningPart(BaseModel):
    """思维链部分"""
    type: Literal["reasoning"] = "reasoning"
    text: str


MessagePart = TextPart | ToolPart | ReasoningPart


class UserMessage(BaseModel):
    """用户消息"""
    id: str = Field(default_factory=lambda: generate_id("msg"))
    role: Literal["user"] = "user"
    session_id: str
    agent: str
    model: str  # provider/model 格式
    parts: list[MessagePart] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class AssistantMessage(BaseModel):
    """助手消息"""
    id: str = Field(default_factory=lambda: generate_id("msg"))
    role: Literal["assistant"] = "assistant"
    session_id: str
    parent_id: str  # 关联的用户消息 ID
    agent: str
    model: str
    parts: list[MessagePart] = Field(default_factory=list)
    finish_reason: Optional[str] = None  # "stop", "tool_calls", "error"
    error: Optional[str] = None
    tokens: dict[str, int] = Field(default_factory=lambda: {
        "input": 0, "output": 0, "total": 0
    })
    cost: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


Message = UserMessage | AssistantMessage


# ============ Agent Models ============

class AgentMode(str, Enum):
    PRIMARY = "primary"      # 主 Agent
    SUBAGENT = "subagent"    # 子 Agent


class AgentConfig(BaseModel):
    """Agent 配置"""
    name: str
    description: Optional[str] = None
    mode: AgentMode = AgentMode.PRIMARY
    model: Optional[str] = None  # 默认模型 provider/model
    system_prompt: Optional[str] = None
    permissions: list[PermissionRule] = Field(default_factory=list)
    max_steps: int = 50  # 最大循环步数
    temperature: float = 0.7


# ============ Session Models ============

def generate_session_id() -> str:
    """生成 5 位小写字母数字混合的会话 ID"""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(5))


class Session(BaseModel):
    """会话"""
    id: str = Field(default_factory=generate_session_id)
    title: str = "New Session"
    agent: str = "build"
    model: str = ""  # provider/model
    parent_id: Optional[str] = None  # 子会话关联父会话
    messages: list[Message] = Field(default_factory=list)
    permissions: list[PermissionRule] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_message(self, message: Message):
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_last_user_message(self) -> Optional[UserMessage]:
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg
        return None

    def get_last_assistant_message(self) -> Optional[AssistantMessage]:
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg
        return None
