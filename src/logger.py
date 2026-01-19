"""
日志系统 - 记录每次 Agent 使用
"""

from __future__ import annotations
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# 日志目录
LOG_DIR = Path(os.getenv("MICO_LOG_DIR", ".mico/logs"))


def setup_logger(
    name: str = "mico",
    log_dir: Path = None,
    level: int = logging.INFO,
    console_output: bool = False
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        log_dir: 日志目录
        level: 日志级别
        console_output: 是否输出到控制台

    Returns:
        Logger 实例
    """
    log_dir = log_dir or LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除现有 handlers
    logger.handlers.clear()

    # 文件 handler - 按日期分割
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)

    # 格式
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台 handler（可选）
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


class AgentLogger:
    """
    Agent 专用日志记录器

    记录：
    - 会话开始/结束
    - 用户输入
    - LLM 调用
    - 工具执行
    - 错误
    """

    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or LOG_DIR
        self.logger = setup_logger("mico", self.log_dir)
        self.session_logger = setup_logger("mico.session", self.log_dir)
        self.tool_logger = setup_logger("mico.tool", self.log_dir)
        self.llm_logger = setup_logger("mico.llm", self.log_dir)

    def _format_data(self, data: Any) -> str:
        """格式化数据为 JSON 字符串"""
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except:
            return str(data)

    # ============ 会话日志 ============

    def session_start(
        self,
        session_id: str,
        agent: str,
        model: str,
        working_dir: str
    ):
        """记录会话开始"""
        self.session_logger.info(
            f"SESSION_START | session={session_id} | agent={agent} | "
            f"model={model} | working_dir={working_dir}"
        )

    def session_end(
        self,
        session_id: str,
        total_steps: int,
        total_tokens: dict,
        total_cost: float
    ):
        """记录会话结束"""
        self.session_logger.info(
            f"SESSION_END | session={session_id} | steps={total_steps} | "
            f"tokens={self._format_data(total_tokens)} | cost={total_cost:.6f}"
        )

    # ============ 用户输入日志 ============

    def user_input(self, session_id: str, message_id: str, text: str):
        """记录用户输入"""
        # 截断过长的输入
        text_preview = text[:500] + "..." if len(text) > 500 else text
        self.logger.info(
            f"USER_INPUT | session={session_id} | message={message_id} | "
            f"text={json.dumps(text_preview, ensure_ascii=False)}"
        )

    # ============ LLM 日志 ============

    def llm_request(
        self,
        session_id: str,
        provider: str,
        model: str,
        messages_count: int,
        tools_count: int
    ):
        """记录 LLM 请求"""
        self.llm_logger.info(
            f"LLM_REQUEST | session={session_id} | provider={provider} | "
            f"model={model} | messages={messages_count} | tools={tools_count}"
        )

    def llm_response(
        self,
        session_id: str,
        finish_reason: str,
        tokens: dict,
        duration_ms: float
    ):
        """记录 LLM 响应"""
        self.llm_logger.info(
            f"LLM_RESPONSE | session={session_id} | finish={finish_reason} | "
            f"tokens={self._format_data(tokens)} | duration_ms={duration_ms:.2f}"
        )

    def llm_error(self, session_id: str, error: str):
        """记录 LLM 错误"""
        self.llm_logger.error(
            f"LLM_ERROR | session={session_id} | error={error}"
        )

    # ============ 工具日志 ============

    def tool_call(
        self,
        session_id: str,
        call_id: str,
        tool_name: str,
        input_data: dict
    ):
        """记录工具调用"""
        input_preview = self._format_data(input_data)
        if len(input_preview) > 500:
            input_preview = input_preview[:500] + "..."
        self.tool_logger.info(
            f"TOOL_CALL | session={session_id} | call={call_id} | "
            f"tool={tool_name} | input={input_preview}"
        )

    def tool_result(
        self,
        session_id: str,
        call_id: str,
        tool_name: str,
        success: bool,
        output_length: int,
        duration_ms: float
    ):
        """记录工具结果"""
        self.tool_logger.info(
            f"TOOL_RESULT | session={session_id} | call={call_id} | "
            f"tool={tool_name} | success={success} | "
            f"output_len={output_length} | duration_ms={duration_ms:.2f}"
        )

    def tool_error(
        self,
        session_id: str,
        call_id: str,
        tool_name: str,
        error: str
    ):
        """记录工具错误"""
        self.tool_logger.error(
            f"TOOL_ERROR | session={session_id} | call={call_id} | "
            f"tool={tool_name} | error={error}"
        )

    # ============ 权限日志 ============

    def permission_request(
        self,
        session_id: str,
        permission: str,
        pattern: str
    ):
        """记录权限请求"""
        self.logger.info(
            f"PERMISSION_REQUEST | session={session_id} | "
            f"permission={permission} | pattern={pattern}"
        )

    def permission_result(
        self,
        session_id: str,
        permission: str,
        pattern: str,
        allowed: bool,
        always: bool = False
    ):
        """记录权限结果"""
        self.logger.info(
            f"PERMISSION_RESULT | session={session_id} | "
            f"permission={permission} | pattern={pattern} | "
            f"allowed={allowed} | always={always}"
        )

    # ============ 通用日志 ============

    def info(self, message: str, **kwargs):
        """通用信息日志"""
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(f"{message} | {extra}" if extra else message)

    def error(self, message: str, **kwargs):
        """通用错误日志"""
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.error(f"{message} | {extra}" if extra else message)

    def debug(self, message: str, **kwargs):
        """通用调试日志"""
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.debug(f"{message} | {extra}" if extra else message)


# 全局日志实例
_logger: Optional[AgentLogger] = None


def get_logger() -> AgentLogger:
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        _logger = AgentLogger()
    return _logger


def set_log_dir(log_dir: Path):
    """设置日志目录"""
    global _logger
    _logger = AgentLogger(log_dir)
