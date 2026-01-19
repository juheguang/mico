"""
UI 模块 - Rich 控制台和显示组件
"""

from .console import console
from .preview import EditStreamPreview
from .message import (
    format_user_message,
    format_assistant_message,
    format_system_message,
    print_user_message,
    print_assistant_message,
    print_system_message,
)
from .tool_display import (
    format_code_with_syntax,
    format_directory_tree,
    format_list_output_simple,
    format_diff,
    detect_language,
)
from .startup import (
    print_ascii_banner,
    print_gradient_text,
    print_welcome_message,
    print_status_bar,
    show_loading_step,
    print_token_stats,
)

__all__ = [
    # 控制台
    "console",
    # 预览
    "EditStreamPreview",
    # 消息格式化
    "format_user_message",
    "format_assistant_message",
    "format_system_message",
    "print_user_message",
    "print_assistant_message",
    "print_system_message",
    # 工具显示
    "format_code_with_syntax",
    "format_directory_tree",
    "format_list_output_simple",
    "format_diff",
    "detect_language",
    # 启动界面
    "print_ascii_banner",
    "print_gradient_text",
    "print_welcome_message",
    "print_status_bar",
    "show_loading_step",
    "print_token_stats",
]
