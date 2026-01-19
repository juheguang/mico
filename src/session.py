"""
会话管理 - 对应 OpenCode 的 session/index.ts
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    Session, Message, UserMessage, AssistantMessage,
    TextPart, ToolPart, ToolCall, ToolState,
    generate_id
)


class SessionManager:
    """会话管理器"""

    def __init__(self, storage_dir: str = ".mico"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, Session] = {}

    def create(
        self,
        agent: str = "build",
        model: str = "",
        title: str = None,
        parent_id: str = None
    ) -> Session:
        """创建新会话"""
        session = Session(
            agent=agent,
            model=model,
            title=title or f"New Session - {datetime.now().isoformat()}",
            parent_id=parent_id
        )
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        # 先从内存查找
        if session_id in self._sessions:
            return self._sessions[session_id]

        # 尝试部分匹配（支持只输入后几位）
        for f in self.storage_dir.glob("*.json"):
            if session_id in f.stem:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                session = Session.model_validate(data)
                self._sessions[session.id] = session
                return session

        return None

    def save(self, session: Session):
        """保存会话到文件"""
        # 文件名包含日期，便于查找；操作仍使用短 ID
        date_part = session.created_at.strftime("%Y%m%d_%H%M%S")
        session_file = self.storage_dir / f"session_{date_part}_{session.id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(
                session.model_dump(mode="json"),
                f,
                indent=2,
                ensure_ascii=False,  # 正确显示中文
                default=str
            )

    def list_sessions(self) -> list[Session]:
        """列出所有会话"""
        sessions = []

        # 从文件系统加载（支持新旧命名格式）
        for session_file in self.storage_dir.glob("*.json"):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = Session.model_validate(data)
                self._sessions[session.id] = session
                sessions.append(session)
            except Exception:
                # 跳过无法解析的文件
                continue

        # 按更新时间排序（最新的在前面）
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def delete(self, session_id: str):
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]

        # 删除包含该 ID 的文件（支持新旧命名）
        for session_file in self.storage_dir.glob("*.json"):
            if session_id in session_file.stem:
                session_file.unlink()


# ============ 消息工具函数 ============

def create_user_message(
    session: Session,
    text: str,
    agent: str = None,
    model: str = None
) -> UserMessage:
    """创建用户消息"""
    message = UserMessage(
        session_id=session.id,
        agent=agent or session.agent,
        model=model or session.model,
        parts=[TextPart(text=text)]
    )
    session.add_message(message)
    return message


def create_assistant_message(
    session: Session,
    parent_id: str,
    agent: str = None,
    model: str = None
) -> AssistantMessage:
    """创建助手消息"""
    message = AssistantMessage(
        session_id=session.id,
        parent_id=parent_id,
        agent=agent or session.agent,
        model=model or session.model
    )
    session.add_message(message)
    return message


def add_text_part(message: AssistantMessage, text: str):
    """添加文本部分"""
    # 查找现有的文本部分或创建新的
    for part in message.parts:
        if isinstance(part, TextPart) and not part.synthetic:
            part.text += text
            return

    message.parts.append(TextPart(text=text))


def add_tool_part(message: AssistantMessage, tool_call: ToolCall) -> ToolPart:
    """添加工具调用部分"""
    part = ToolPart(tool_call=tool_call)
    message.parts.append(part)
    return part


def update_tool_part(
    message: AssistantMessage,
    call_id: str,
    state: ToolState,
    output: str = None,
    error: str = None
):
    """更新工具调用状态"""
    for part in message.parts:
        if isinstance(part, ToolPart) and part.tool_call.id == call_id:
            part.tool_call.state = state
            part.tool_call.output = output
            part.tool_call.error = error
            if state == ToolState.RUNNING:
                part.tool_call.start_time = datetime.now()
            elif state in (ToolState.COMPLETED, ToolState.ERROR):
                part.tool_call.end_time = datetime.now()
            return


def messages_to_openai_format(messages: list[Message]) -> list[dict]:
    """将消息转换为 OpenAI API 格式"""
    result = []

    for msg in messages:
        if msg.role == "user":
            # 用户消息
            text_parts = [p.text for p in msg.parts if isinstance(p, TextPart)]
            result.append({
                "role": "user",
                "content": "\n".join(text_parts)
            })

        elif msg.role == "assistant":
            # 助手消息
            content = ""
            tool_calls = []

            for part in msg.parts:
                if isinstance(part, TextPart):
                    content += part.text
                elif isinstance(part, ToolPart):
                    tc = part.tool_call
                    tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.tool_name,
                            "arguments": json.dumps(tc.input)
                        }
                    })

            # 确保 content 或 tool_calls 至少有一个
            # 某些 API (如 DeepSeek) 要求必须设置其中之一
            if not content and not tool_calls:
                # 跳过空的 assistant 消息
                continue

            msg_dict = {"role": "assistant"}
            # 始终设置 content 字段（即使为空字符串也要设置，某些 API 需要）
            if content or not tool_calls:
                msg_dict["content"] = content or ""
            if tool_calls:
                msg_dict["tool_calls"] = tool_calls

            result.append(msg_dict)

            # 添加工具结果
            for part in msg.parts:
                if isinstance(part, ToolPart):
                    tc = part.tool_call
                    if tc.state in (ToolState.COMPLETED, ToolState.ERROR):
                        result.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tc.output or tc.error or ""
                        })

    return result
