"""
Code Review Agent - Reviews code diffs using local LLM models.

This agent demonstrates:
- Prompt engineering for code review tasks
- Context limit handling for local models
- Structured output parsing

Usage:
    python -m src.agents.code_review --diff path/to/diff.patch
    git diff | python -m src.agents.code_review --stdin
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import TextIO

from ..common.ollama_client import (
    OllamaClient,
    OllamaConfig,
    OllamaError,
    estimate_tokens,
)


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"  # Security, crashes, data loss
    HIGH = "high"          # Bugs, logic errors
    MEDIUM = "medium"      # Code quality, maintainability
    LOW = "low"            # Style, minor improvements
    INFO = "info"          # Suggestions, observations


@dataclass
class ReviewIssue:
    """A single issue found during code review."""
    severity: Severity
    category: str
    file: str
    line: int | None
    title: str
    description: str
    suggestion: str | None = None


@dataclass
class ReviewResult:
    """Complete code review result."""
    summary: str
    issues: list[ReviewIssue] = field(default_factory=list)
    positive_notes: list[str] = field(default_factory=list)
    raw_response: str = ""
    model_used: str = ""
    tokens_used: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)

    @property
    def has_blocking_issues(self) -> bool:
        return self.critical_count > 0 or self.high_count > 0


# Context limits for common models (in tokens)
MODEL_CONTEXT_LIMITS = {
    "llama3.1:latest": 8192,
    "llama3.1:8b": 8192,
    "llama3.1:70b": 8192,
    "llama3.2:latest": 8192,
    "llama3.3:latest": 131072,
    "llama3.3:70b": 131072,
    "deepseek-r1:latest": 65536,
    "deepseek-r1:7b": 65536,
    "deepseek-r1:70b": 65536,
    "codellama:latest": 16384,
    "qwen2.5-coder:latest": 32768,
    "default": 4096,  # Safe default for unknown models
}


SYSTEM_PROMPT = """You are an expert code reviewer. Your job is to review code diffs and provide actionable, constructive feedback.

Guidelines:
- Focus on correctness, security, and maintainability
- Be specific - reference exact lines and code
- Provide concrete suggestions, not vague criticism
- Acknowledge good patterns when you see them
- Prioritize issues by severity
- Be constructive, not harsh

Output Format:
You MUST structure your response as follows:

## Summary
A 1-2 sentence overview of the changes and your overall assessment.

## Issues
For each issue found, use this exact format:
[SEVERITY: critical|high|medium|low|info]
[CATEGORY: bug|security|performance|style|logic|error-handling|documentation|testing]
[FILE: filename]
[LINE: line_number or "N/A"]
**Title**: Brief issue title
**Description**: What the problem is
**Suggestion**: How to fix it

## Positive Notes
- List any good practices or improvements you noticed
- Each item on its own line starting with "-"

If there are no issues, say "No issues found." in the Issues section.
If there's nothing positive to note, omit the Positive Notes section."""


REVIEW_PROMPT_TEMPLATE = """Review the following code diff:

```diff
{diff}
```

{context}

Provide your code review following the specified format."""


def get_context_limit(model: str) -> int:
    """Get context token limit for a model."""
    # Try exact match first
    if model in MODEL_CONTEXT_LIMITS:
        return MODEL_CONTEXT_LIMITS[model]

    # Try base model name (before :)
    base_model = model.split(":")[0]
    for key, limit in MODEL_CONTEXT_LIMITS.items():
        if key.startswith(base_model):
            return limit

    return MODEL_CONTEXT_LIMITS["default"]


def truncate_diff(diff: str, max_tokens: int, reserve_tokens: int = 1500) -> tuple[str, bool]:
    """
    Truncate diff to fit within context limit.

    Args:
        diff: The full diff text
        max_tokens: Maximum tokens for the entire context
        reserve_tokens: Tokens to reserve for system prompt and response

    Returns:
        Tuple of (truncated_diff, was_truncated)
    """
    available_tokens = max_tokens - reserve_tokens
    estimated_tokens = estimate_tokens(diff)

    if estimated_tokens <= available_tokens:
        return diff, False

    # Calculate target length (chars = tokens * 4 approximately)
    target_chars = available_tokens * 4

    # Try to truncate intelligently by keeping complete hunks
    lines = diff.split("\n")
    truncated_lines = []
    current_chars = 0
    truncation_note = "\n... [diff truncated due to context limits] ...\n"

    for line in lines:
        if current_chars + len(line) + 1 > target_chars - len(truncation_note):
            # Find a good break point (end of a hunk)
            break
        truncated_lines.append(line)
        current_chars += len(line) + 1

    # Try to end at a hunk boundary (line starting with @@)
    for i in range(len(truncated_lines) - 1, max(0, len(truncated_lines) - 50), -1):
        if truncated_lines[i].startswith("@@") or truncated_lines[i].startswith("diff --git"):
            truncated_lines = truncated_lines[:i]
            break

    truncated = "\n".join(truncated_lines) + truncation_note
    return truncated, True


def parse_severity(text: str) -> Severity:
    """Parse severity from text."""
    text_lower = text.lower().strip()
    for severity in Severity:
        if severity.value in text_lower:
            return severity
    return Severity.MEDIUM


def parse_review_response(response: str) -> ReviewResult:
    """
    Parse structured review response into ReviewResult.

    This handles the output format specified in SYSTEM_PROMPT.
    """
    result = ReviewResult(summary="", raw_response=response)

    # Extract summary
    summary_match = re.search(
        r"##\s*Summary\s*\n(.*?)(?=\n##|\Z)",
        response,
        re.DOTALL | re.IGNORECASE
    )
    if summary_match:
        result.summary = summary_match.group(1).strip()

    # Extract issues
    issues_match = re.search(
        r"##\s*Issues\s*\n(.*?)(?=\n##|\Z)",
        response,
        re.DOTALL | re.IGNORECASE
    )
    if issues_match:
        issues_text = issues_match.group(1)
        if "no issues found" not in issues_text.lower():
            result.issues = parse_issues(issues_text)

    # Extract positive notes
    positive_match = re.search(
        r"##\s*Positive\s*Notes?\s*\n(.*?)(?=\n##|\Z)",
        response,
        re.DOTALL | re.IGNORECASE
    )
    if positive_match:
        notes_text = positive_match.group(1).strip()
        result.positive_notes = [
            line.lstrip("- ").strip()
            for line in notes_text.split("\n")
            if line.strip() and line.strip() != "-"
        ]

    return result


def parse_issues(issues_text: str) -> list[ReviewIssue]:
    """Parse individual issues from the issues section."""
    issues = []

    # Split on severity markers
    issue_blocks = re.split(r'\n(?=\[SEVERITY:)', issues_text)

    for block in issue_blocks:
        if not block.strip():
            continue

        issue = parse_single_issue(block)
        if issue:
            issues.append(issue)

    return issues


def parse_single_issue(block: str) -> ReviewIssue | None:
    """Parse a single issue block."""
    severity = Severity.MEDIUM
    category = "general"
    file = "unknown"
    line = None
    title = ""
    description = ""
    suggestion = None

    # Extract severity
    severity_match = re.search(r'\[SEVERITY:\s*([^\]]+)\]', block, re.IGNORECASE)
    if severity_match:
        severity = parse_severity(severity_match.group(1))

    # Extract category
    category_match = re.search(r'\[CATEGORY:\s*([^\]]+)\]', block, re.IGNORECASE)
    if category_match:
        category = category_match.group(1).strip()

    # Extract file
    file_match = re.search(r'\[FILE:\s*([^\]]+)\]', block, re.IGNORECASE)
    if file_match:
        file = file_match.group(1).strip()

    # Extract line
    line_match = re.search(r'\[LINE:\s*([^\]]+)\]', block, re.IGNORECASE)
    if line_match:
        line_text = line_match.group(1).strip()
        if line_text.lower() not in ("n/a", "na", "none", "-"):
            try:
                # Handle ranges like "10-15" by taking the first number
                line = int(re.match(r'\d+', line_text).group())
            except (ValueError, AttributeError):
                pass

    # Extract title
    title_match = re.search(r'\*\*Title\*\*:\s*(.+?)(?=\n|$)', block)
    if title_match:
        title = title_match.group(1).strip()

    # Extract description
    desc_match = re.search(
        r'\*\*Description\*\*:\s*(.+?)(?=\*\*Suggestion\*\*|\Z)',
        block,
        re.DOTALL
    )
    if desc_match:
        description = desc_match.group(1).strip()

    # Extract suggestion
    suggest_match = re.search(r'\*\*Suggestion\*\*:\s*(.+?)(?=\n\n|\[SEVERITY|\Z)', block, re.DOTALL)
    if suggest_match:
        suggestion = suggest_match.group(1).strip()

    if not title and not description:
        return None

    return ReviewIssue(
        severity=severity,
        category=category,
        file=file,
        line=line,
        title=title or "Untitled Issue",
        description=description or title,
        suggestion=suggestion,
    )


class CodeReviewAgent:
    """Agent for reviewing code diffs using local LLMs."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        model: str | None = None,
        verbose: bool = False,
    ):
        self.client = client or OllamaClient()
        self.model = model or self.client.config.default_model
        self.verbose = verbose

    def review(
        self,
        diff: str,
        context: str | None = None,
        stream: bool = True,
    ) -> ReviewResult:
        """
        Review a code diff.

        Args:
            diff: The diff text to review
            context: Optional additional context about the changes
            stream: Whether to stream output (shows progress)

        Returns:
            ReviewResult with parsed feedback
        """
        if not diff.strip():
            return ReviewResult(
                summary="No changes to review.",
                model_used=self.model,
            )

        # Check context limits and truncate if needed
        context_limit = get_context_limit(self.model)
        diff, was_truncated = truncate_diff(diff, context_limit)

        if was_truncated and self.verbose:
            print(f"[Note: Diff truncated to fit {context_limit} token context limit]",
                  file=sys.stderr)

        # Build prompt
        context_text = f"\nAdditional context: {context}" if context else ""
        prompt = REVIEW_PROMPT_TEMPLATE.format(diff=diff, context=context_text)

        if self.verbose:
            estimated = estimate_tokens(prompt) + estimate_tokens(SYSTEM_PROMPT)
            print(f"[Estimated prompt tokens: {estimated}]", file=sys.stderr)

        # Generate review
        if stream:
            response_text = self._generate_streaming(prompt)
        else:
            response = self.client.generate(
                prompt=prompt,
                model=self.model,
                system=SYSTEM_PROMPT,
                stream=False,
            )
            response_text = response.response

        # Parse response
        result = parse_review_response(response_text)
        result.model_used = self.model
        result.tokens_used = estimate_tokens(response_text)

        return result

    def _generate_streaming(self, prompt: str) -> str:
        """Generate with streaming output to show progress."""
        full_response = []

        print("\n--- Code Review ---\n", file=sys.stderr)

        for chunk in self.client.generate(
            prompt=prompt,
            model=self.model,
            system=SYSTEM_PROMPT,
            stream=True,
        ):
            text = chunk.response
            full_response.append(text)
            print(text, end="", flush=True)

        print("\n", file=sys.stderr)
        return "".join(full_response)


def format_review_output(result: ReviewResult) -> str:
    """Format review result for terminal output."""
    output = []

    # Header
    output.append("=" * 60)
    output.append("CODE REVIEW RESULTS")
    output.append("=" * 60)

    # Summary
    output.append(f"\n{result.summary}\n")

    # Statistics
    if result.issues:
        stats = f"Found {len(result.issues)} issue(s): "
        counts = []
        if result.critical_count:
            counts.append(f"{result.critical_count} critical")
        if result.high_count:
            counts.append(f"{result.high_count} high")
        medium = sum(1 for i in result.issues if i.severity == Severity.MEDIUM)
        if medium:
            counts.append(f"{medium} medium")
        low = sum(1 for i in result.issues if i.severity == Severity.LOW)
        if low:
            counts.append(f"{low} low")
        info = sum(1 for i in result.issues if i.severity == Severity.INFO)
        if info:
            counts.append(f"{info} info")
        output.append(stats + ", ".join(counts))
    else:
        output.append("No issues found!")

    # Issues
    if result.issues:
        output.append("\n" + "-" * 40)
        output.append("ISSUES")
        output.append("-" * 40)

        for i, issue in enumerate(result.issues, 1):
            severity_icon = {
                Severity.CRITICAL: "[!!!]",
                Severity.HIGH: "[!!]",
                Severity.MEDIUM: "[!]",
                Severity.LOW: "[.]",
                Severity.INFO: "[i]",
            }.get(issue.severity, "[?]")

            output.append(f"\n{i}. {severity_icon} {issue.title}")
            output.append(f"   Severity: {issue.severity.value.upper()}")
            output.append(f"   Category: {issue.category}")
            output.append(f"   Location: {issue.file}" + (f":{issue.line}" if issue.line else ""))
            output.append(f"   {issue.description}")
            if issue.suggestion:
                output.append(f"   Suggestion: {issue.suggestion}")

    # Positive notes
    if result.positive_notes:
        output.append("\n" + "-" * 40)
        output.append("POSITIVE NOTES")
        output.append("-" * 40)
        for note in result.positive_notes:
            output.append(f"  + {note}")

    # Footer
    output.append("\n" + "=" * 60)
    output.append(f"Model: {result.model_used}")
    if result.has_blocking_issues:
        output.append("Status: REVIEW REQUIRED (blocking issues found)")
    else:
        output.append("Status: LOOKS GOOD (no blocking issues)")
    output.append("=" * 60)

    return "\n".join(output)


def read_diff(source: str | TextIO) -> str:
    """Read diff from file path or stdin."""
    if isinstance(source, str):
        with open(source, "r") as f:
            return f.read()
    return source.read()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Review code diffs using local LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review a patch file
  python -m src.agents.code_review --diff changes.patch

  # Review git diff from stdin
  git diff | python -m src.agents.code_review --stdin

  # Review staged changes
  git diff --cached | python -m src.agents.code_review --stdin

  # Use a specific model
  git diff | python -m src.agents.code_review --stdin --model codellama:latest

  # Add context about the changes
  git diff | python -m src.agents.code_review --stdin --context "Fixing auth bug"
        """
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--diff", "-d",
        help="Path to diff/patch file"
    )
    input_group.add_argument(
        "--stdin", "-s",
        action="store_true",
        help="Read diff from stdin"
    )

    parser.add_argument(
        "--model", "-m",
        help="Ollama model to use (default: from env or llama3.1:latest)"
    )
    parser.add_argument(
        "--context", "-c",
        help="Additional context about the changes"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output including token estimates"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming output"
    )

    args = parser.parse_args()

    # Read diff
    if args.stdin:
        diff = sys.stdin.read()
    else:
        try:
            diff = read_diff(args.diff)
        except FileNotFoundError:
            print(f"Error: File not found: {args.diff}", file=sys.stderr)
            sys.exit(1)
        except IOError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    if not diff.strip():
        print("No diff content to review.", file=sys.stderr)
        sys.exit(0)

    # Create agent
    try:
        config = OllamaConfig.from_env()
        if args.model:
            config.default_model = args.model
        client = OllamaClient(config)

        # Check if Ollama is available
        if not client.is_available():
            print(
                "Error: Cannot connect to Ollama. "
                "Please ensure Ollama is running (systemctl status ollama)",
                file=sys.stderr
            )
            sys.exit(1)

        agent = CodeReviewAgent(
            client=client,
            model=args.model,
            verbose=args.verbose,
        )

    except OllamaError as e:
        print(f"Error initializing agent: {e}", file=sys.stderr)
        sys.exit(1)

    # Run review
    try:
        result = agent.review(
            diff=diff,
            context=args.context,
            stream=not args.no_stream,
        )

        # Output results
        if args.json:
            output = {
                "summary": result.summary,
                "issues": [
                    {
                        "severity": i.severity.value,
                        "category": i.category,
                        "file": i.file,
                        "line": i.line,
                        "title": i.title,
                        "description": i.description,
                        "suggestion": i.suggestion,
                    }
                    for i in result.issues
                ],
                "positive_notes": result.positive_notes,
                "model_used": result.model_used,
                "has_blocking_issues": result.has_blocking_issues,
            }
            print(json.dumps(output, indent=2))
        else:
            print(format_review_output(result))

        # Exit with non-zero if blocking issues found
        sys.exit(1 if result.has_blocking_issues else 0)

    except OllamaError as e:
        print(f"Error during review: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nReview cancelled.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
