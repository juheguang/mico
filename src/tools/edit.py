"""
编辑文件工具
"""

import os
from pathlib import Path
from .base import BaseTool, ToolContext, ToolResult


class EditTool(BaseTool):
    """编辑文件工具"""

    name = "edit"
    description = """Edit a file by replacing text.
Provide the exact text to find and the text to replace it with.
If the file doesn't exist and old_string is empty, a new file will be created."""

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit"
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact text to find and replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace it with"
                }
            },
            "required": ["file_path", "old_string", "new_string"]
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        file_path = params["file_path"]
        old_string = params["old_string"]
        new_string = params["new_string"]

        # 解析路径
        if not os.path.isabs(file_path):
            file_path = ctx.working_dir / file_path
        else:
            file_path = Path(file_path)

        # 检查权限
        await ctx.ask_permission("edit", [str(file_path)], {
            "file": str(file_path),
            "operation": "create" if old_string == "" else "edit"
        })

        try:
            # 创建新文件
            if old_string == "":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_string)
                return ToolResult(
                    output=f"Created file: {file_path}",
                    title=str(file_path),
                    metadata={"operation": "create"}
                )

            # 编辑现有文件
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return ToolResult(
                    output=f"old_string not found in {file_path}",
                    error="not_found"
                )

            # 检查是否有多个匹配
            count = content.count(old_string)
            if count > 1:
                return ToolResult(
                    output=f"Found {count} matches. Provide more context in old_string to identify a unique match.",
                    error="multiple_matches"
                )

            # 执行替换
            new_content = content.replace(old_string, new_string, 1)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                output="Edit applied successfully.",
                title=str(file_path),
                metadata={"operation": "edit"}
            )

        except Exception as e:
            return ToolResult(output=str(e), error=str(e))
