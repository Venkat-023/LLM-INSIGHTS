"""Interactive LangSmith playground CLI.

This app is intentionally small and beginner-friendly. The goal is to create
interesting traced runs that make LangSmith's traces, metadata, tags, latency,
token usage, and error views easy to explore.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from config import AppSettings, load_settings
from llm import LLMClient, LLMResponse, TokenUsage
from prompts import PromptSpec, get_prompt
from tracing import traceable_run
from utils import (
    ensure_directory,
    format_token_summary,
    multiline_input,
    normalize_whitespace,
    safe_slug,
)

console = Console()


@dataclass
class RunRecord:
    """A local session record used for summaries and exports."""

    feature: str
    prompt_name: str
    started_at: datetime
    latency_seconds: float
    success: bool
    tokens_total: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    error: str = ""
    response_preview: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class PlaygroundApp:
    """Small terminal app that creates rich, nested LangSmith traces."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.session_dir = ensure_directory(settings.session_dir)
        self.history: list[dict[str, str]] = []
        self.records: list[RunRecord] = []
        self.llm = LLMClient(settings=settings)
        self.logger = self._build_logger()

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"langsmith_playground.{self.settings.session_id}")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not logger.handlers:
            log_path = self.session_dir / "activity.log"
            handler = logging.FileHandler(log_path, encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def run(self) -> None:
        console.clear()
        self._print_header()
        while True:
            self._print_menu()
            choice = Prompt.ask("Select an option", choices=[str(i) for i in range(1, 9)])

            if choice == "1":
                self.chat()
            elif choice == "2":
                self.compare_prompts()
            elif choice == "3":
                self.summarize_text()
            elif choice == "4":
                self.explain_code()
            elif choice == "5":
                self.observability_lab()
            elif choice == "6":
                self.simulate_error()
            elif choice == "7":
                self.show_session_info()
            elif choice == "8":
                self.exit_app()
                break

    def _print_header(self) -> None:
        header = Panel.fit(
            Text("LangSmith Playground", style="bold cyan"),
            subtitle=f"Session: {self.settings.session_id}",
            border_style="cyan",
        )
        console.print(header)
        config_lines = [
            f"LangSmith tracing: {'enabled' if self.settings.langsmith_tracing else 'disabled'}",
            f"LangSmith API key: {'set' if self.settings.langsmith_api_key else 'missing'}",
            f"LLM provider: {self.settings.llm_provider}",
            f"Model: {self.settings.model_name}",
        ]
        console.print(
            Panel(
                "\n".join(config_lines)
                + "\n\nA learning tool for traces, runs, prompts, metadata, tags, latency, tokens, and errors.",
                border_style="blue",
            )
        )

    def _print_menu(self) -> None:
        menu = Table.grid(padding=(0, 2))
        menu.add_column(style="bold magenta")
        menu.add_column(style="white")
        menu.add_row("1.", "Chat")
        menu.add_row("2.", "Compare Prompts")
        menu.add_row("3.", "Summarize Text")
        menu.add_row("4.", "Explain Code")
        menu.add_row("5.", "Observability Lab")
        menu.add_row("6.", "Simulate Error")
        menu.add_row("7.", "View Session Info")
        menu.add_row("8.", "Exit")
        console.print(Panel(menu, title="Menu", border_style="magenta"))

    def _base_metadata(self, feature: str, prompt_name: str | None = None) -> dict[str, Any]:
        metadata = {
            "user_id": self.settings.user_id,
            "session_id": self.settings.session_id,
            "feature": feature,
            "environment": self.settings.environment,
            "experiment": self.settings.experiment,
            "language": self.settings.language,
        }
        if prompt_name:
            metadata["prompt_name"] = prompt_name
        return metadata

    def _base_tags(self, *extra: str) -> list[str]:
        tags = ["demo", "tutorial", "playground", "langsmith", "testing"]
        tags.extend(extra)
        return tags

    def _record_run(self, record: RunRecord) -> None:
        self.records.append(record)
        self.logger.info(
            "prompt=%s feature=%s latency=%.3f tokens=%s success=%s error=%s",
            record.prompt_name,
            record.feature,
            record.latency_seconds,
            record.tokens_total,
            record.success,
            record.error,
        )

    def _show_result_panel(self, title: str, body: str, style: str = "green") -> None:
        console.print(Panel(body, title=title, border_style=style))

    @traceable_run(
        name="Chat Request",
        run_type="chain",
        tags=["chat", "demo", "tutorial", "playground", "langsmith"],
    )
    def chat(self) -> None:
        """Chat is split into child runs so LangSmith shows the reasoning steps.

        In the dashboard, this helps demonstrate the parent trace, a prompt build
        step, the model run, and the final rendering step.
        """

        question = Prompt.ask("What would you like to ask?")
        if not question.strip():
            console.print("[yellow]Skipping empty question.[/]")
            return

        started = time.perf_counter()
        feature_metadata = self._base_metadata("chat")
        try:
            prompt_payload = self._build_chat_prompt(question)
            response = self._run_chat_llm(prompt_payload)
            rendered = self._render_chat_output(question, response)
            self._append_history("user", question)
            self._append_history("assistant", response.content)
            elapsed = time.perf_counter() - started
            tokens = response.token_usage
            self._record_run(
                RunRecord(
                    feature="chat",
                    prompt_name="free-form chat",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=True,
                    tokens_total=tokens.total,
                    tokens_prompt=tokens.prompt,
                    tokens_completion=tokens.completion,
                    response_preview=response.content[:240],
                    metadata=feature_metadata,
                )
            )
            self._show_result_panel("Chat Response", rendered, "green")
            self._show_metrics(elapsed, tokens)
            self._offer_retry(self.chat)
        except Exception as exc:  # noqa: BLE001 - this is a demo app
            elapsed = time.perf_counter() - started
            self._record_run(
                RunRecord(
                    feature="chat",
                    prompt_name="free-form chat",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=False,
                    error=str(exc),
                    metadata=feature_metadata,
                )
            )
            console.print(Panel(str(exc), title="Chat Error", border_style="red"))

    @traceable_run(name="Build Chat Prompt", run_type="chain")
    def _build_chat_prompt(self, question: str) -> list[dict[str, str]]:
        """This child run shows the exact prompt structure in LangSmith."""

        system_prompt = (
            "You are a helpful, concise assistant in a LangSmith learning demo. "
            "Answer clearly and include practical detail."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        return messages

    @traceable_run(name="LLM Call", run_type="llm")
    def _run_chat_llm(self, prompt_messages: list[dict[str, str]]) -> LLMResponse:
        """The model run is what produces token usage and latency in LangSmith."""

        return self.llm.generate(
            prompt_messages=prompt_messages,
            feature="chat",
            prompt_name="free-form chat",
            metadata=self._base_metadata("chat"),
            tags=self._base_tags("chat"),
        )

    @traceable_run(name="Parse Response", run_type="chain")
    def _render_chat_output(self, question: str, response: LLMResponse) -> str:
        """This run demonstrates post-processing and a clean response hand-off."""

        return (
            f"Question:\n{question}\n\n"
            f"Answer:\n{response.content}\n\n"
            f"{format_token_summary(response.token_usage)}"
        )

    def _append_history(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def _show_metrics(self, latency: float, tokens: TokenUsage) -> None:
        table = Table(title="Request Metrics", expand=False)
        table.add_column("Metric")
        table.add_column("Value", style="bold cyan")
        table.add_row("Latency", f"{latency:.2f}s")
        table.add_row("Prompt tokens", str(tokens.prompt))
        table.add_row("Completion tokens", str(tokens.completion))
        table.add_row("Total tokens", str(tokens.total))
        console.print(table)

    def _offer_retry(self, callback) -> None:
        if not self.records:
            return
        if Confirm.ask("Retry this action?", default=False):
            callback()

    @traceable_run(
        name="Compare Prompts",
        run_type="chain",
        tags=["comparison", "demo", "tutorial", "playground", "langsmith"],
    )
    def compare_prompts(self) -> None:
        """Run the same question through four prompts to compare behavior."""

        question = Prompt.ask("Ask one question to compare across prompts")
        if not question.strip():
            console.print("[yellow]Skipping empty question.[/]")
            return

        started = time.perf_counter()
        results: list[tuple[PromptSpec, LLMResponse]] = []

        for prompt_name in [
            "helpful_assistant",
            "senior_python_engineer",
            "eli5_teacher",
            "pirate",
        ]:
            spec = get_prompt(prompt_name)
            response = self._run_prompt_variant(spec, question)
            results.append((spec, response))

        elapsed = time.perf_counter() - started
        self._display_compare_results(question, results)
        total_tokens = sum(item[1].token_usage.total for item in results)
        self._record_run(
            RunRecord(
                feature="comparison",
                prompt_name="compare prompts",
                started_at=datetime.now(),
                latency_seconds=elapsed,
                success=True,
                tokens_total=total_tokens,
                tokens_prompt=sum(item[1].token_usage.prompt for item in results),
                tokens_completion=sum(item[1].token_usage.completion for item in results),
                response_preview=" | ".join(item[1].content[:40] for item in results),
                metadata=self._base_metadata("comparison"),
            )
        )
        self._show_metrics(
            elapsed,
            TokenUsage(
                prompt=sum(item[1].token_usage.prompt for item in results),
                completion=sum(item[1].token_usage.completion for item in results),
                total=total_tokens,
            ),
        )

    @traceable_run(name="Prompt Variant", run_type="chain")
    def _run_prompt_variant(self, spec: PromptSpec, question: str) -> LLMResponse:
        """Each variant becomes a child run so LangSmith shows side-by-side traces."""

        messages = [
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": question},
        ]
        return self.llm.generate(
            prompt_messages=messages,
            feature="comparison",
            prompt_name=spec.name,
            metadata=self._base_metadata("comparison", spec.name),
            tags=self._base_tags("comparison", safe_slug(spec.name)),
        )

    @traceable_run(name="Display Comparison", run_type="chain")
    def _display_compare_results(
        self, question: str, results: list[tuple[PromptSpec, LLMResponse]]
    ) -> None:
        """A compact UI step that is visible in LangSmith as a trace child."""

        columns = []
        for spec, response in results:
            body = Text(response.content)
            columns.append(
                Panel(
                    body,
                    title=spec.name,
                    subtitle=spec.description,
                    border_style="cyan",
                )
            )

        console.print(Panel(f"Question: {question}", border_style="magenta"))
        console.print(Columns(columns, equal=True, expand=True))

    @traceable_run(
        name="Summarize Text",
        run_type="chain",
        tags=["summary", "demo", "tutorial", "playground", "langsmith"],
    )
    def summarize_text(self) -> None:
        text = multiline_input(
            "Paste text to summarize",
            end_token="END",
            console=console,
        )
        if not normalize_whitespace(text):
            console.print("[yellow]No text entered.[/]")
            return

        started = time.perf_counter()
        try:
            cleaned = self._preprocess_summary_text(text)
            summary = self._run_summary_llm(cleaned)
            postprocessed = self._postprocess_summary(summary)
            elapsed = time.perf_counter() - started
            self._record_run(
                RunRecord(
                    feature="summary",
                    prompt_name="summarize text",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=True,
                    tokens_total=summary.token_usage.total,
                    tokens_prompt=summary.token_usage.prompt,
                    tokens_completion=summary.token_usage.completion,
                    response_preview=postprocessed[:240],
                    metadata=self._base_metadata("summary"),
                )
            )
            self._show_result_panel("Summary", postprocessed, "green")
            self._show_metrics(elapsed, summary.token_usage)
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - started
            self._record_run(
                RunRecord(
                    feature="summary",
                    prompt_name="summarize text",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=False,
                    error=str(exc),
                    metadata=self._base_metadata("summary"),
                )
            )
            console.print(Panel(str(exc), title="Summary Error", border_style="red"))

    @traceable_run(name="Preprocessing", run_type="chain")
    def _preprocess_summary_text(self, text: str) -> str:
        """This child run shows text cleanup before the model sees it."""

        return normalize_whitespace(text)

    @traceable_run(name="LLM", run_type="llm")
    def _run_summary_llm(self, text: str) -> LLMResponse:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise summarizer. Return a short summary, "
                    "three bullet points, and one practical takeaway."
                ),
            },
            {"role": "user", "content": text},
        ]
        return self.llm.generate(
            prompt_messages=messages,
            feature="summary",
            prompt_name="summarize text",
            metadata=self._base_metadata("summary"),
            tags=self._base_tags("summary"),
        )

    @traceable_run(name="Postprocessing", run_type="chain")
    def _postprocess_summary(self, response: LLMResponse) -> str:
        """This child run demonstrates formatting after the model returns."""

        return f"{response.content}\n\n{format_token_summary(response.token_usage)}"

    @traceable_run(
        name="Explain Code",
        run_type="chain",
        tags=["code", "demo", "tutorial", "playground", "langsmith"],
    )
    def explain_code(self) -> None:
        code = multiline_input(
            "Paste Python code",
            end_token="END",
            console=console,
        )
        if not normalize_whitespace(code):
            console.print("[yellow]No code entered.[/]")
            return

        started = time.perf_counter()
        try:
            explanation = self._explain_code_stage("explanation", code)
            complexity = self._explain_code_stage("complexity", code)
            improvements = self._explain_code_stage("improvements", code)
            elapsed = time.perf_counter() - started
            combined_tokens = (
                explanation.token_usage.total
                + complexity.token_usage.total
                + improvements.token_usage.total
            )
            self._record_run(
                RunRecord(
                    feature="code",
                    prompt_name="explain code",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=True,
                    tokens_total=combined_tokens,
                    tokens_prompt=(
                        explanation.token_usage.prompt
                        + complexity.token_usage.prompt
                        + improvements.token_usage.prompt
                    ),
                    tokens_completion=(
                        explanation.token_usage.completion
                        + complexity.token_usage.completion
                        + improvements.token_usage.completion
                    ),
                    response_preview=explanation.content[:120],
                    metadata=self._base_metadata("code"),
                )
            )

            console.print(Panel(Syntax(code, "python", theme="monokai", line_numbers=True), title="Input Code", border_style="blue"))
            self._show_result_panel("Explanation", explanation.content, "green")
            self._show_result_panel("Complexity", complexity.content, "yellow")
            self._show_result_panel("Improvements", improvements.content, "magenta")
            self._show_metrics(
                elapsed,
                TokenUsage(
                    prompt=(
                        explanation.token_usage.prompt
                        + complexity.token_usage.prompt
                        + improvements.token_usage.prompt
                    ),
                    completion=(
                        explanation.token_usage.completion
                        + complexity.token_usage.completion
                        + improvements.token_usage.completion
                    ),
                    total=combined_tokens,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - started
            self._record_run(
                RunRecord(
                    feature="code",
                    prompt_name="explain code",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=False,
                    error=str(exc),
                    metadata=self._base_metadata("code"),
                )
            )
            console.print(Panel(str(exc), title="Code Explanation Error", border_style="red"))

    @traceable_run(name="Stage Analysis", run_type="chain")
    def _explain_code_stage(self, stage: str, code: str) -> LLMResponse:
        """Separate child runs make LangSmith show a clear explanation pipeline."""

        stage_prompts = {
            "explanation": "Explain what the Python code does in plain language.",
            "complexity": "Analyze time and space complexity. Mention assumptions.",
            "improvements": "Suggest concrete improvements, refactors, and edge cases.",
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior Python engineer helping a beginner learn. "
                    "Be specific, structured, and kind."
                ),
            },
            {
                "role": "user",
                "content": f"{stage_prompts[stage]}\n\nCode:\n{code}",
            },
        ]
        return self.llm.generate(
            prompt_messages=messages,
            feature="code",
            prompt_name=f"code:{stage}",
            metadata=self._base_metadata("code", stage),
            tags=self._base_tags("code", stage),
        )

    @traceable_run(
        name="Observability Lab",
        run_type="chain",
        tags=["observability", "tokens", "latency", "analytics", "demo", "langsmith"],
    )
    def observability_lab(self) -> None:
        """Create comparable traces for token, latency, and metadata analysis."""

        topic = Prompt.ask("Topic for the observability test", default="LangSmith observability")
        started = time.perf_counter()
        scenarios = self._build_observability_scenarios(topic)
        results: list[tuple[str, int, LLMResponse]] = []

        try:
            for scenario_name, prompt_messages in scenarios:
                estimated_input_tokens = self._estimate_prompt_tokens(prompt_messages)
                response = self._run_observability_scenario(
                    scenario_name=scenario_name,
                    prompt_messages=prompt_messages,
                    estimated_input_tokens=estimated_input_tokens,
                )
                results.append((scenario_name, estimated_input_tokens, response))

            elapsed = time.perf_counter() - started
            self._display_observability_results(results, elapsed)

            combined_tokens = TokenUsage(
                prompt=sum(result[2].token_usage.prompt for result in results),
                completion=sum(result[2].token_usage.completion for result in results),
                total=sum(result[2].token_usage.total for result in results),
            )
            self._record_run(
                RunRecord(
                    feature="observability",
                    prompt_name="token consumption lab",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=True,
                    tokens_total=combined_tokens.total,
                    tokens_prompt=combined_tokens.prompt,
                    tokens_completion=combined_tokens.completion,
                    response_preview="token lab completed",
                    metadata=self._base_metadata("observability", "token consumption lab"),
                )
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - started
            self._record_run(
                RunRecord(
                    feature="observability",
                    prompt_name="token consumption lab",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=False,
                    error=str(exc),
                    metadata=self._base_metadata("observability", "token consumption lab"),
                )
            )
            console.print(Panel(str(exc), title="Observability Lab Error", border_style="red"))

    @traceable_run(name="Build Observability Scenarios", run_type="chain")
    def _build_observability_scenarios(self, topic: str) -> list[tuple[str, list[dict[str, str]]]]:
        """These prompt sizes make token growth visible in LangSmith charts."""

        base_system = (
            "You are helping test LLM observability. Answer clearly and keep a structured format."
        )
        short_prompt = f"Explain {topic} in one sentence."
        medium_prompt = (
            f"Explain {topic} for a beginner. Include a definition, two benefits, "
            "two risks, and one practical example."
        )
        long_prompt = (
            f"Create a detailed learning note about {topic}. Include sections for overview, "
            "dashboard metrics, token usage, latency, errors, metadata, tags, experiments, "
            "and a checklist for what to inspect after each run. Keep it concise but complete."
        )

        return [
            (
                "short-input",
                [{"role": "system", "content": base_system}, {"role": "user", "content": short_prompt}],
            ),
            (
                "medium-input",
                [{"role": "system", "content": base_system}, {"role": "user", "content": medium_prompt}],
            ),
            (
                "long-input",
                [{"role": "system", "content": base_system}, {"role": "user", "content": long_prompt}],
            ),
        ]

    @traceable_run(name="Observability Scenario", run_type="llm")
    def _run_observability_scenario(
        self,
        *,
        scenario_name: str,
        prompt_messages: list[dict[str, str]],
        estimated_input_tokens: int,
    ) -> LLMResponse:
        metadata = self._base_metadata("observability", scenario_name)
        metadata.update(
            {
                "scenario": scenario_name,
                "estimated_input_tokens": estimated_input_tokens,
                "observability_focus": "token_usage_latency_metadata_tags",
            }
        )
        return self.llm.generate(
            prompt_messages=prompt_messages,
            feature="observability",
            prompt_name=scenario_name,
            metadata=metadata,
            tags=self._base_tags("observability", "tokens", "latency", scenario_name),
        )

    @traceable_run(name="Display Observability Results", run_type="chain")
    def _display_observability_results(
        self, results: list[tuple[str, int, LLMResponse]], elapsed: float
    ) -> None:
        table = Table(title="Observability Lab Results", expand=True)
        table.add_column("Scenario", style="bold cyan")
        table.add_column("Est. Input Tokens", justify="right")
        table.add_column("Prompt Tokens", justify="right")
        table.add_column("Completion Tokens", justify="right")
        table.add_column("Total Tokens", justify="right")
        table.add_column("Latency", justify="right")

        for scenario_name, estimated_input_tokens, response in results:
            table.add_row(
                scenario_name,
                str(estimated_input_tokens),
                str(response.token_usage.prompt),
                str(response.token_usage.completion),
                str(response.token_usage.total),
                f"{response.latency_seconds:.2f}s",
            )

        console.print(table)
        console.print(
            Panel(
                "In LangSmith, filter by tags `observability` and `tokens`, then compare "
                "token usage, latency, metadata, and child run hierarchy.",
                title=f"Total Wall Time: {elapsed:.2f}s",
                border_style="cyan",
            )
        )

    def _estimate_prompt_tokens(self, prompt_messages: list[dict[str, str]]) -> int:
        prompt_text = "\n".join(message["content"] for message in prompt_messages)
        return max(1, len(prompt_text.split()))

    @traceable_run(
        name="Simulate Error",
        run_type="tool",
        tags=["error", "demo", "tutorial", "playground", "langsmith"],
    )
    def simulate_error(self) -> None:
        """This deliberately fails so LangSmith can show a failed run trace."""

        started = time.perf_counter()
        try:
            self._failing_tool()
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - started
            self._record_run(
                RunRecord(
                    feature="error",
                    prompt_name="simulate error",
                    started_at=datetime.now(),
                    latency_seconds=elapsed,
                    success=False,
                    error=str(exc),
                    metadata=self._base_metadata("error"),
                )
            )
            console.print(Panel(str(exc), title="Expected Failure", border_style="red"))
            self._offer_retry(self.simulate_error)

    @traceable_run(name="Failing Tool", run_type="tool")
    def _failing_tool(self) -> None:
        raise ValueError("Artificial failure for LangSmith demo")

    @traceable_run(name="Session Info", run_type="chain")
    def show_session_info(self) -> None:
        total_requests = len(self.records)
        successes = sum(1 for record in self.records if record.success)
        failures = total_requests - successes
        average_latency = (
            sum(record.latency_seconds for record in self.records) / total_requests
            if total_requests
            else 0.0
        )
        total_tokens = sum(record.tokens_total for record in self.records)

        table = Table(title="Session Information", expand=False)
        table.add_column("Field")
        table.add_column("Value", style="bold cyan")
        table.add_row("Session ID", self.settings.session_id)
        table.add_row("Total requests", str(total_requests))
        table.add_row("Average latency", f"{average_latency:.2f}s")
        table.add_row("Total tokens", str(total_tokens))
        table.add_row("Successful runs", str(successes))
        table.add_row("Failed runs", str(failures))
        console.print(table)

        if self.history and Confirm.ask("Export conversation history to Markdown?", default=True):
            path = self.export_conversation_markdown()
            console.print(f"[green]Exported conversation to[/] {path}")

    def export_conversation_markdown(self) -> Path:
        export_path = self.session_dir / "conversation.md"
        lines = [
            "# LangSmith Playground Conversation",
            "",
            f"- Session ID: {self.settings.session_id}",
            f"- Exported: {datetime.now().isoformat(timespec='seconds')}",
            "",
        ]
        for item in self.history:
            role = item["role"].title()
            lines.append(f"## {role}")
            lines.append("")
            lines.append(item["content"])
            lines.append("")
        export_path.write_text("\n".join(lines), encoding="utf-8")
        return export_path

    def exit_app(self) -> None:
        total_tokens = sum(record.tokens_total for record in self.records)
        total_requests = len(self.records)
        successes = sum(1 for record in self.records if record.success)
        failures = total_requests - successes
        average_latency = (
            sum(record.latency_seconds for record in self.records) / total_requests
            if total_requests
            else 0.0
        )
        summary = Panel(
            f"Requests: {total_requests}\n"
            f"Successes: {successes}\n"
            f"Failures: {failures}\n"
            f"Average latency: {average_latency:.2f}s\n"
            f"Total tokens: {total_tokens}",
            title="Session Summary",
            border_style="cyan",
        )
        console.print(summary)


def main() -> None:
    settings = load_settings()
    app = PlaygroundApp(settings)
    app.run()


if __name__ == "__main__":
    main()
