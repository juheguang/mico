"""
权限系统 - 对应 OpenCode 的 permission/next.ts
"""

from __future__ import annotations
import fnmatch
from typing import Callable, Optional
from rich.console import Console
from rich.prompt import Prompt

from .models import PermissionAction, PermissionRule

console = Console()


class PermissionDeniedError(Exception):
    """权限被拒绝"""
    pass


class PermissionRejectedError(Exception):
    """用户拒绝授权"""
    pass


class PermissionManager:
    """权限管理器"""

    def __init__(
        self,
        rules: list[PermissionRule] = None,
        ask_callback: Optional[Callable[[str, str, dict], bool]] = None
    ):
        self.rules = rules or []
        self.approved: list[PermissionRule] = []  # 运行时批准的规则
        self.ask_callback = ask_callback or self._default_ask

    def _default_ask(self, permission: str, pattern: str, metadata: dict) -> bool:
        """默认的询问用户函数"""
        console.print(f"\n[bold yellow]⚠️  Permission Request[/bold yellow]")
        console.print(f"  Permission: [cyan]{permission}[/cyan]")
        console.print(f"  Pattern: [cyan]{pattern}[/cyan]")
        if metadata:
            console.print(f"  Details: {metadata}")
        console.print("[dim]Choose one: y = allow once, n = deny, always = allow for this pattern[/dim]")

        response = Prompt.ask(
            "Allow this action? (y/n/always)",
            choices=["y", "n", "always"],
            default="n"
        )

        if response == "always":
            # 记住这个决定
            self.approved.append(PermissionRule(
                permission=permission,
                pattern=pattern,
                action=PermissionAction.ALLOW
            ))
            return True
        return response == "y"

    def evaluate(self, permission: str, pattern: str) -> PermissionAction:
        """
        评估权限，返回应该采取的动作

        规则匹配顺序：
        1. 运行时批准的规则
        2. 配置的规则（后面的优先）
        """
        # 合并规则，运行时批准的优先级最高
        all_rules = self.rules + self.approved

        # 从后往前查找匹配的规则（后定义的优先）
        for rule in reversed(all_rules):
            if self._match(permission, rule.permission) and self._match(pattern, rule.pattern):
                return rule.action

        # 默认需要询问
        return PermissionAction.ASK

    def _match(self, value: str, pattern: str) -> bool:
        """通配符匹配"""
        if pattern == "*":
            return True
        return fnmatch.fnmatch(value, pattern)

    async def check(
        self,
        permission: str,
        patterns: list[str],
        metadata: dict = None,
        always_patterns: list[str] = None
    ):
        """
        检查权限，如果需要会询问用户

        Args:
            permission: 权限名（如 "bash", "edit"）
            patterns: 要检查的模式列表（如文件路径、命令）
            metadata: 额外信息，用于显示给用户
            always_patterns: 用户选择"always"时记住的模式
        """
        for pattern in patterns:
            action = self.evaluate(permission, pattern)

            if action == PermissionAction.DENY:
                raise PermissionDeniedError(
                    f"Permission '{permission}' denied for pattern '{pattern}'"
                )

            if action == PermissionAction.ASK:
                allowed = self.ask_callback(permission, pattern, metadata or {})
                if not allowed:
                    raise PermissionRejectedError(
                        f"User rejected permission '{permission}' for '{pattern}'"
                    )

    def add_rule(self, rule: PermissionRule):
        """添加规则"""
        self.rules.append(rule)

    def merge_rules(self, rules: list[PermissionRule]):
        """合并规则"""
        self.rules.extend(rules)


# ============ 默认权限规则 ============

DEFAULT_RULES = [
    # 默认允许大部分操作
    PermissionRule(permission="*", pattern="*", action=PermissionAction.ALLOW),
    # 敏感操作需要询问
    PermissionRule(permission="bash", pattern="rm *", action=PermissionAction.ASK),
    PermissionRule(permission="bash", pattern="sudo *", action=PermissionAction.ASK),
    PermissionRule(permission="edit", pattern="*.env", action=PermissionAction.ASK),
    PermissionRule(permission="edit", pattern="*.env.*", action=PermissionAction.ASK),
    # doom loop 检测
    PermissionRule(permission="doom_loop", pattern="*", action=PermissionAction.ASK),
]


def create_default_permission_manager() -> PermissionManager:
    """创建默认权限管理器"""
    return PermissionManager(rules=DEFAULT_RULES.copy())
