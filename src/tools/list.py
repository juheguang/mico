"""
列出目录工具
"""

import os
from pathlib import Path
from .base import BaseTool, ToolContext, ToolResult


class ListTool(BaseTool):
    """列出目录内容"""

    name = "list"
    description = """List files and directories in a path.
Similar to 'ls -la' but formatted for AI consumption."""

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: current directory)"
                }
            }
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        path = params.get("path", ".")

        if not os.path.isabs(path):
            path = ctx.working_dir / path
        else:
            path = Path(path)

        try:
            dirs = []
            files = []
            for entry in sorted(path.iterdir()):
                if entry.name.startswith("."):
                    continue  # 跳过隐藏文件
                if entry.is_dir():
                    dirs.append(f"📁 {entry.name}")
                else:
                    files.append(f"📄 {entry.name}")
            
            # 目录在前，文件在后
            entries = dirs + files

            return ToolResult(
                output="\n".join(entries) if entries else "Empty directory",
                title=str(path),
                metadata={"count": len(entries)}
            )
        except Exception as e:
            return ToolResult(output=str(e), error=str(e))
