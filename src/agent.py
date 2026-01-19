"""
Agent 配置与管理 - 对应 OpenCode 的 agent/agent.ts
"""

from __future__ import annotations
from typing import Optional

from .models import AgentConfig, AgentMode, PermissionRule, PermissionAction


# ============ 内置 Agent 定义 ============

SYSTEM_PROMPT_BUILD = """You are an expert software engineer with deep knowledge of programming languages, frameworks, and best practices.

You have access to tools that allow you to read, edit, and create files, as well as execute bash commands.

## Guidelines

1. **Understand First**: Before making changes, read relevant files to understand the codebase structure and conventions.

2. **Make Minimal Changes**: Only modify what's necessary to accomplish the task. Don't refactor unrelated code.

3. **Explain Your Actions**: Briefly explain what you're doing and why before using tools.

4. **Handle Errors Gracefully**: If a tool fails, analyze the error and try a different approach.

5. **Verify Your Work**: After making changes, consider running tests or checking that the code works as expected.

## Working Directory

You are working in: {working_dir}

## Current Date

{current_date}
"""

SYSTEM_PROMPT_PLAN = """You are a senior software architect focused ONLY on analysis and planning.

You must NOT execute tools or modify files. Your job is to reason, ask questions, and produce a plan.

## Your Role

1. **Analyze**: Understand the request and high-level architecture.
2. **Clarify**: Ask questions when requirements are missing or ambiguous.
3. **Plan**: Produce a clear, step-by-step implementation plan.
4. **Advise**: Provide risks, edge cases, and testing ideas.

## Strict Rules

- You may call ask_user for clarification when needed.
- You may use read/glob/list to inspect files (read-only tools).
- Do NOT call edit.
- You can ask to use bash tools.
- If information is missing, ask the user first (prefer ask_user if structured choices help).
- Only after clarification, provide a plan. 
- Please ask the user to switch to Build Agent mode and start working at the end.


## Output Format

When planning, respond with:
1. **Assumptions**
2. **Plan** (numbered steps)
3. **Risks & Edge Cases**
4. **Testing Suggestions**

## Working Directory

You are working in: {working_dir}
"""


def create_build_agent(working_dir: str = ".") -> AgentConfig:
    """创建 build Agent（默认全能 Agent）"""
    return AgentConfig(
        name="build",
        description="Default agent for development work with full access",
        mode=AgentMode.PRIMARY,
        system_prompt=SYSTEM_PROMPT_BUILD.format(
            working_dir=working_dir,
            current_date=__import__("datetime").date.today().isoformat()
        ),
        permissions=[
            PermissionRule(permission="*", pattern="*", action=PermissionAction.ALLOW),
            PermissionRule(permission="bash", pattern="rm -rf *", action=PermissionAction.ASK),
            PermissionRule(permission="bash", pattern="sudo *", action=PermissionAction.ASK),
            PermissionRule(permission="edit", pattern="*.env", action=PermissionAction.ASK),
        ],
        max_steps=50,
        temperature=0.7
    )


def create_plan_agent(working_dir: str = ".") -> AgentConfig:
    """创建 plan Agent（只读分析 Agent）"""
    return AgentConfig(
        name="plan",
        description="Read-only agent for analysis and planning",
        mode=AgentMode.PRIMARY,
        system_prompt=SYSTEM_PROMPT_PLAN.format(working_dir=working_dir),
        permissions=[
            # 只允许读取操作
            PermissionRule(permission="read", pattern="*", action=PermissionAction.ALLOW),
            PermissionRule(permission="glob", pattern="*", action=PermissionAction.ALLOW),
            PermissionRule(permission="list", pattern="*", action=PermissionAction.ALLOW),
            # 拒绝写入操作
            PermissionRule(permission="edit", pattern="*", action=PermissionAction.DENY),
            PermissionRule(permission="bash", pattern="*", action=PermissionAction.ASK),
        ],
        max_steps=30,
        temperature=0.5
    )


def create_explore_agent() -> AgentConfig:
    """创建 explore Agent（快速探索子 Agent）"""
    return AgentConfig(
        name="explore",
        description="Fast agent for exploring codebases",
        mode=AgentMode.SUBAGENT,
        permissions=[
            PermissionRule(permission="read", pattern="*", action=PermissionAction.ALLOW),
            PermissionRule(permission="glob", pattern="*", action=PermissionAction.ALLOW),
            PermissionRule(permission="list", pattern="*", action=PermissionAction.ALLOW),
            PermissionRule(permission="bash", pattern="grep *", action=PermissionAction.ALLOW),
            PermissionRule(permission="bash", pattern="find *", action=PermissionAction.ALLOW),
            # 拒绝其他操作
            PermissionRule(permission="edit", pattern="*", action=PermissionAction.DENY),
        ],
        max_steps=20,
        temperature=0.3
    )


# ============ Agent 管理器 ============

class AgentManager:
    """Agent 管理器"""

    def __init__(self, working_dir: str = "."):
        self.working_dir = working_dir
        self._agents: dict[str, AgentConfig] = {}
        self._load_builtin_agents()

    def _load_builtin_agents(self):
        """加载内置 Agent"""
        self._agents["build"] = create_build_agent(self.working_dir)
        self._agents["plan"] = create_plan_agent(self.working_dir)
        self._agents["explore"] = create_explore_agent()

    def get(self, name: str) -> Optional[AgentConfig]:
        """获取 Agent 配置"""
        return self._agents.get(name)

    def list(self) -> list[AgentConfig]:
        """列出所有 Agent"""
        return list(self._agents.values())

    def register(self, agent: AgentConfig):
        """注册自定义 Agent"""
        self._agents[agent.name] = agent

    def default_agent(self) -> AgentConfig:
        """获取默认 Agent"""
        return self._agents["build"]
