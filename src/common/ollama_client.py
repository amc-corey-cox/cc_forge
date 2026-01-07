"""
Ollama client for interacting with local LLM models.

This module provides a simple interface to Ollama's REST API for
text generation and chat completions.
"""

import json
import os
from dataclasses import dataclass
from typing import Iterator
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


@dataclass
class OllamaConfig:
    """Configuration for Ollama client."""
    host: str = "127.0.0.1"
    port: int = 11434
    default_model: str = "llama3.1:latest"
    timeout: int = 120  # seconds

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("OLLAMA_HOST", "127.0.0.1"),
            port=int(os.getenv("OLLAMA_PORT", "11434")),
            default_model=os.getenv("OLLAMA_MODEL", "llama3.1:latest"),
            timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
        )


@dataclass
class GenerateResponse:
    """Response from Ollama generate endpoint."""
    response: str
    model: str
    done: bool
    total_duration: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None

    @property
    def tokens_per_second(self) -> float | None:
        """Calculate generation tokens per second if timing data available."""
        if self.total_duration and self.eval_count:
            # total_duration is in nanoseconds
            seconds = self.total_duration / 1e9
            return self.eval_count / seconds if seconds > 0 else None
        return None


class OllamaError(Exception):
    """Base exception for Ollama client errors."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when unable to connect to Ollama server."""
    pass


class OllamaModelError(OllamaError):
    """Raised when model-related errors occur."""
    pass


class OllamaClient:
    """Client for Ollama REST API."""

    def __init__(self, config: OllamaConfig | None = None):
        self.config = config or OllamaConfig.from_env()

    def _request(self, endpoint: str, data: dict) -> dict:
        """Make a POST request to Ollama API."""
        url = f"{self.config.base_url}{endpoint}"
        payload = json.dumps(data).encode("utf-8")

        req = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urlopen(req, timeout=self.config.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 404:
                raise OllamaModelError(f"Model not found: {data.get('model')}")
            raise OllamaError(f"HTTP error {e.code}: {e.reason}")
        except URLError as e:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.config.base_url}. "
                f"Is Ollama running? Error: {e.reason}"
            )
        except TimeoutError:
            raise OllamaError(
                f"Request timed out after {self.config.timeout}s. "
                "Try a smaller prompt or increase timeout."
            )

    def _stream_request(self, endpoint: str, data: dict) -> Iterator[dict]:
        """Make a streaming POST request to Ollama API."""
        url = f"{self.config.base_url}{endpoint}"
        payload = json.dumps(data).encode("utf-8")

        req = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urlopen(req, timeout=self.config.timeout) as response:
                for line in response:
                    if line:
                        yield json.loads(line.decode("utf-8"))
        except HTTPError as e:
            if e.code == 404:
                raise OllamaModelError(f"Model not found: {data.get('model')}")
            raise OllamaError(f"HTTP error {e.code}: {e.reason}")
        except URLError as e:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.config.base_url}. "
                f"Is Ollama running? Error: {e.reason}"
            )

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        stream: bool = False,
        options: dict | None = None,
    ) -> GenerateResponse | Iterator[GenerateResponse]:
        """
        Generate text completion from a prompt.

        Args:
            prompt: The prompt to generate from
            model: Model to use (defaults to config default)
            system: System prompt to set context
            stream: Whether to stream the response
            options: Additional model options (temperature, num_predict, etc.)

        Returns:
            GenerateResponse or iterator of responses if streaming
        """
        model = model or self.config.default_model

        data = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }

        if system:
            data["system"] = system
        if options:
            data["options"] = options

        if stream:
            return self._generate_stream(data)

        response = self._request("/api/generate", data)
        return GenerateResponse(
            response=response.get("response", ""),
            model=response.get("model", model),
            done=response.get("done", True),
            total_duration=response.get("total_duration"),
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
        )

    def _generate_stream(self, data: dict) -> Iterator[GenerateResponse]:
        """Stream generate responses."""
        for chunk in self._stream_request("/api/generate", data):
            yield GenerateResponse(
                response=chunk.get("response", ""),
                model=chunk.get("model", data["model"]),
                done=chunk.get("done", False),
                total_duration=chunk.get("total_duration"),
                prompt_eval_count=chunk.get("prompt_eval_count"),
                eval_count=chunk.get("eval_count"),
            )

    def list_models(self) -> list[dict]:
        """List available models."""
        url = f"{self.config.base_url}/api/tags"
        req = Request(url, method="GET")

        try:
            with urlopen(req, timeout=self.config.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("models", [])
        except (HTTPError, URLError) as e:
            raise OllamaConnectionError(f"Failed to list models: {e}")

    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            self.list_models()
            return True
        except OllamaError:
            return False

    def get_model_info(self, model: str | None = None) -> dict | None:
        """Get info about a specific model."""
        model = model or self.config.default_model
        models = self.list_models()

        for m in models:
            if m.get("name") == model or m.get("model") == model:
                return m
        return None


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count for a text.

    Uses a simple heuristic: ~4 characters per token for English text.
    This is approximate - actual tokenization varies by model.
    """
    return len(text) // 4
