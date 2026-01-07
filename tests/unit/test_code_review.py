"""Unit tests for the code review agent."""

import pytest
from src.agents.code_review import (
    CodeReviewAgent,
    ReviewResult,
    ReviewIssue,
    Severity,
    parse_review_response,
    parse_severity,
    parse_issues,
    parse_single_issue,
    truncate_diff,
    get_context_limit,
    format_review_output,
)
from src.common.ollama_client import estimate_tokens


class TestSeverityParsing:
    """Tests for severity parsing."""

    def test_parse_critical(self):
        assert parse_severity("critical") == Severity.CRITICAL
        assert parse_severity("CRITICAL") == Severity.CRITICAL
        assert parse_severity(" critical ") == Severity.CRITICAL

    def test_parse_high(self):
        assert parse_severity("high") == Severity.HIGH
        assert parse_severity("HIGH") == Severity.HIGH

    def test_parse_medium(self):
        assert parse_severity("medium") == Severity.MEDIUM
        assert parse_severity("MEDIUM") == Severity.MEDIUM

    def test_parse_low(self):
        assert parse_severity("low") == Severity.LOW

    def test_parse_info(self):
        assert parse_severity("info") == Severity.INFO

    def test_parse_unknown_defaults_to_medium(self):
        assert parse_severity("unknown") == Severity.MEDIUM
        assert parse_severity("") == Severity.MEDIUM


class TestTokenEstimation:
    """Tests for token estimation."""

    def test_estimate_tokens_short_text(self):
        # ~4 chars per token
        text = "Hello World!"  # 12 chars
        assert estimate_tokens(text) == 3

    def test_estimate_tokens_empty(self):
        assert estimate_tokens("") == 0

    def test_estimate_tokens_longer_text(self):
        text = "a" * 400  # 400 chars = 100 tokens
        assert estimate_tokens(text) == 100


class TestContextLimits:
    """Tests for context limit handling."""

    def test_known_model_limit(self):
        assert get_context_limit("llama3.1:latest") == 8192
        assert get_context_limit("llama3.3:70b") == 131072

    def test_base_model_matching(self):
        # Should match base model name
        assert get_context_limit("llama3.1:custom") == 8192

    def test_unknown_model_default(self):
        assert get_context_limit("unknown-model") == 4096


class TestDiffTruncation:
    """Tests for diff truncation."""

    def test_no_truncation_needed(self):
        diff = "small diff"
        result, was_truncated = truncate_diff(diff, max_tokens=8192)
        assert result == diff
        assert not was_truncated

    def test_truncation_applied(self):
        # Create a large diff
        large_diff = "\n".join([
            "diff --git a/file.py b/file.py",
            "@@ -1,10 +1,10 @@",
            *[f"+line {i}" for i in range(1000)],
        ])
        result, was_truncated = truncate_diff(large_diff, max_tokens=500)
        assert was_truncated
        assert len(result) < len(large_diff)
        assert "truncated" in result.lower()


class TestIssueParsing:
    """Tests for parsing individual issues."""

    def test_parse_complete_issue(self):
        block = """[SEVERITY: high]
[CATEGORY: bug]
[FILE: src/main.py]
[LINE: 42]
**Title**: Missing null check
**Description**: The function doesn't check for null input
**Suggestion**: Add a null check at the beginning"""

        issue = parse_single_issue(block)

        assert issue is not None
        assert issue.severity == Severity.HIGH
        assert issue.category == "bug"
        assert issue.file == "src/main.py"
        assert issue.line == 42
        assert issue.title == "Missing null check"
        assert "null" in issue.description.lower()
        assert "null check" in issue.suggestion.lower()

    def test_parse_issue_without_line(self):
        block = """[SEVERITY: medium]
[CATEGORY: style]
[FILE: README.md]
[LINE: N/A]
**Title**: Missing documentation
**Description**: No API documentation provided"""

        issue = parse_single_issue(block)

        assert issue is not None
        assert issue.line is None

    def test_parse_issue_minimal(self):
        block = """[SEVERITY: low]
[CATEGORY: style]
[FILE: test.py]
[LINE: 5]
**Title**: Unused import
**Description**: Import is not used"""

        issue = parse_single_issue(block)

        assert issue is not None
        assert issue.suggestion is None


class TestReviewResponseParsing:
    """Tests for parsing complete review responses."""

    def test_parse_full_response(self):
        response = """## Summary
This PR adds a new feature with some minor issues.

## Issues
[SEVERITY: high]
[CATEGORY: security]
[FILE: auth.py]
[LINE: 15]
**Title**: SQL Injection vulnerability
**Description**: User input is not sanitized
**Suggestion**: Use parameterized queries

[SEVERITY: low]
[CATEGORY: style]
[FILE: utils.py]
[LINE: 30]
**Title**: Long line
**Description**: Line exceeds 80 characters
**Suggestion**: Break into multiple lines

## Positive Notes
- Good use of type hints
- Clear function names
"""
        result = parse_review_response(response)

        assert "new feature" in result.summary.lower()
        assert len(result.issues) == 2
        assert result.issues[0].severity == Severity.HIGH
        assert result.issues[1].severity == Severity.LOW
        assert len(result.positive_notes) == 2

    def test_parse_no_issues_response(self):
        response = """## Summary
Code looks good!

## Issues
No issues found.

## Positive Notes
- Clean code
"""
        result = parse_review_response(response)

        assert len(result.issues) == 0
        assert len(result.positive_notes) == 1

    def test_parse_response_without_positive_notes(self):
        response = """## Summary
Minor changes reviewed.

## Issues
No issues found.
"""
        result = parse_review_response(response)

        assert len(result.positive_notes) == 0


class TestReviewResult:
    """Tests for ReviewResult class."""

    def test_critical_count(self):
        result = ReviewResult(summary="test")
        result.issues = [
            ReviewIssue(Severity.CRITICAL, "bug", "f.py", 1, "t", "d"),
            ReviewIssue(Severity.CRITICAL, "bug", "f.py", 2, "t", "d"),
            ReviewIssue(Severity.HIGH, "bug", "f.py", 3, "t", "d"),
        ]
        assert result.critical_count == 2

    def test_has_blocking_issues(self):
        result = ReviewResult(summary="test")
        result.issues = [
            ReviewIssue(Severity.CRITICAL, "bug", "f.py", 1, "t", "d"),
        ]
        assert result.has_blocking_issues

    def test_no_blocking_issues(self):
        result = ReviewResult(summary="test")
        result.issues = [
            ReviewIssue(Severity.MEDIUM, "style", "f.py", 1, "t", "d"),
            ReviewIssue(Severity.LOW, "style", "f.py", 2, "t", "d"),
        ]
        assert not result.has_blocking_issues


class TestOutputFormatting:
    """Tests for output formatting."""

    def test_format_with_issues(self):
        result = ReviewResult(
            summary="Test review",
            model_used="test-model",
        )
        result.issues = [
            ReviewIssue(
                severity=Severity.HIGH,
                category="bug",
                file="test.py",
                line=10,
                title="Test Issue",
                description="A test issue",
                suggestion="Fix it",
            )
        ]

        output = format_review_output(result)

        assert "Test review" in output
        assert "HIGH" in output
        assert "test.py" in output
        assert "Test Issue" in output
        assert "REVIEW REQUIRED" in output

    def test_format_without_issues(self):
        result = ReviewResult(
            summary="All good!",
            model_used="test-model",
        )

        output = format_review_output(result)

        assert "All good!" in output
        assert "No issues found" in output
        assert "LOOKS GOOD" in output


# Integration test that requires Ollama (skipped by default)
@pytest.mark.skip(reason="Requires running Ollama instance")
class TestCodeReviewAgentIntegration:
    """Integration tests requiring Ollama."""

    def test_simple_review(self):
        agent = CodeReviewAgent()
        diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,5 @@
+import os
+
 def hello():
-    print("hello")
+    print(os.getenv("GREETING", "hello"))
"""
        result = agent.review(diff, stream=False)
        assert result.summary
        assert result.model_used
