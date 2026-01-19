"""
读取文件工具
"""

import os
from pathlib import Path
from .base import BaseTool, ToolContext, ToolResult


class ReadTool(BaseTool):
    """读取文件工具"""

    name = "read"
    description = """Read the contents of a file.
Use this to examine code, configuration, or any text file."""

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read"
                }
            },
            "required": ["file_path"]
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        file_path = params["file_path"]
        offset = params.get("offset", 1)
        limit = params.get("limit")

        # 解析路径
        if not os.path.isabs(file_path):
            file_path = ctx.working_dir / file_path
        else:
            file_path = Path(file_path)

        # 检查权限
        await ctx.ask_permission("read", [str(file_path)])

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 应用 offset 和 limit
            start = max(0, offset - 1)
            end = start + limit if limit else len(lines)
            selected_lines = lines[start:end]

            # 添加行号
            output_lines = []
            for i, line in enumerate(selected_lines, start=start + 1):
                output_lines.append(f"{i:6}|{line.rstrip()}")

            return ToolResult(
                output="\n".join(output_lines),
                title=str(file_path),
                metadata={"total_lines": len(lines)}
            )

        except FileNotFoundError:
            return ToolResult(
                output=f"File not found: {file_path}",
                error="file_not_found"
            )
        except Exception as e:
            return ToolResult(output=str(e), error=str(e))
