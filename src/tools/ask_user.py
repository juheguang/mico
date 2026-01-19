"""
交互式提问工具
"""

from __future__ import annotations
import json
from typing import Any
from rich.prompt import Prompt

from .base import BaseTool, ToolContext, ToolResult


class AskUserTool(BaseTool):
    """让模型向用户提出一组问题并收集答案"""

    name = "ask_user"
    description = (
        "Use this when you need to confirm uncertain content or user preferences."
        "Ask the user a set of questions (single or multi-choice) and return answers. "
        "Questions will be asked one by one in the terminal."
    )

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Optional title for the questionnaire"
                },
                "questions": {
                    "type": "array",
                    "description": "List of questions to ask",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question text"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["single", "multi"],
                                "description": "single or multi choice"
                            },
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of options"
                            }
                        },
                        "required": ["question", "type", "options"]
                    }
                }
            },
            "required": ["questions"]
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        title = params.get("title", "")
        questions = params.get("questions", [])

        if not questions:
            return ToolResult(
                output="No questions provided.",
                error="questions_empty"
            )

        if title:
            from rich.console import Console
            console = Console()
            console.print(f"\n[bold cyan]🧩 {title}[/bold cyan]")

        answers = []
        for idx, q in enumerate(questions, start=1):
            question_text = str(q.get("question", "")).strip()
            q_type = q.get("type", "single")
            options = q.get("options", [])

            if not question_text or not options:
                answers.append({
                    "question": question_text or f"Question {idx}",
                    "type": q_type,
                    "selected": [],
                    "error": "invalid_question"
                })
                continue

            # 显示题目
            from rich.console import Console
            console = Console()
            console.print(f"\n[bold]Q{idx}.[/bold] {question_text}")
            for opt_idx, opt in enumerate(options, start=1):
                console.print(f"  [dim]{opt_idx}.[/dim] {opt}")

            if q_type == "multi":
                # 多选：输入逗号分隔的编号
                raw = Prompt.ask("Select options (comma-separated numbers)", default="")
                selections = []
                if raw.strip():
                    parts = [p.strip() for p in raw.split(",") if p.strip()]
                    for p in parts:
                        if p.isdigit():
                            i = int(p)
                            if 1 <= i <= len(options):
                                selections.append(options[i - 1])
                answers.append({
                    "question": question_text,
                    "type": "multi",
                    "selected": selections
                })
            else:
                # 单选：输入编号
                raw = Prompt.ask("Select one option (number)", default="1")
                selected = []
                if raw.strip().isdigit():
                    i = int(raw.strip())
                    if 1 <= i <= len(options):
                        selected = [options[i - 1]]
                answers.append({
                    "question": question_text,
                    "type": "single",
                    "selected": selected
                })

        # 汇总输出
        summary_lines = []
        for a in answers:
            selected = a.get("selected", [])
            if selected:
                summary_lines.append(f"- {a['question']}: {', '.join(selected)}")
            else:
                summary_lines.append(f"- {a['question']}: (no selection)")

        result = {
            "title": title,
            "answers": answers,
            "summary": "\n".join(summary_lines)
        }

        return ToolResult(
            output=json.dumps(result, ensure_ascii=False),
            title=title or "ask_user_result",
            metadata={"count": len(answers)}
        )
