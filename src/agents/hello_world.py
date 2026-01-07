#!/usr/bin/env python3
"""
Hello World Agent - First agent for CC Forge

This is a learning exercise that demonstrates:
1. How to connect to a local Ollama instance
2. What the response format looks like
3. Latency characteristics of local inference

Usage:
    python -m src.agents.hello_world
    # or
    python src/agents/hello_world.py

Environment Variables:
    OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
    OLLAMA_MODEL: Model to use (default: llama3.1:latest)
"""

import json
import os
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


# Configuration from environment (never hardcode system-specific values)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:latest")


def check_ollama_connection() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        req = Request(f"{OLLAMA_HOST}/api/tags")
        with urlopen(req, timeout=5) as response:
            return response.status == 200
    except (URLError, TimeoutError):
        return False


def list_available_models() -> list[str]:
    """Get list of models available on the Ollama server."""
    try:
        req = Request(f"{OLLAMA_HOST}/api/tags")
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return [model["name"] for model in data.get("models", [])]
    except (URLError, TimeoutError, json.JSONDecodeError):
        return []


def generate(prompt: str, model: str = OLLAMA_MODEL) -> dict[str, Any]:
    """
    Send a prompt to Ollama and get a response.

    This uses the /api/generate endpoint which is simpler than /api/chat.
    For multi-turn conversations, use /api/chat instead.

    Returns:
        Dictionary containing:
        - response: The generated text
        - model: Model used
        - total_duration: Total time in nanoseconds
        - load_duration: Time to load model (if cold start)
        - prompt_eval_count: Number of tokens in prompt
        - prompt_eval_duration: Time to process prompt (ns)
        - eval_count: Number of tokens generated
        - eval_duration: Time to generate response (ns)
    """
    url = f"{OLLAMA_HOST}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,  # Get complete response at once
    }

    req = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    start_time = time.perf_counter()

    with urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode())

    end_time = time.perf_counter()

    # Add wall clock time for comparison
    result["wall_clock_seconds"] = end_time - start_time

    return result


def format_duration(nanoseconds: int) -> str:
    """Convert nanoseconds to human-readable format."""
    seconds = nanoseconds / 1_000_000_000
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    return f"{seconds:.2f}s"


def calculate_tokens_per_second(tokens: int, duration_ns: int) -> float:
    """Calculate tokens per second from token count and duration in nanoseconds."""
    if duration_ns == 0:
        return 0.0
    seconds = duration_ns / 1_000_000_000
    return tokens / seconds


def main():
    """Run the Hello World agent demonstration."""
    print("=" * 60)
    print("CC Forge - Hello World Agent")
    print("=" * 60)
    print()

    # Step 1: Check connection
    print(f"Connecting to Ollama at {OLLAMA_HOST}...")
    if not check_ollama_connection():
        print("ERROR: Cannot connect to Ollama.")
        print("Make sure Ollama is running:")
        print("  - Check: systemctl status ollama-cpu")
        print("  - Start: sudo systemctl start ollama-cpu")
        sys.exit(1)
    print("Connected!")
    print()

    # Step 2: List available models
    print("Available models:")
    models = list_available_models()
    if not models:
        print("  (none found - pull a model with: ollama pull llama3.1:latest)")
    else:
        for model in models:
            marker = " <-- using this" if model == OLLAMA_MODEL else ""
            print(f"  - {model}{marker}")
    print()

    # Check if our target model is available
    if models and OLLAMA_MODEL not in models:
        print(f"WARNING: Model '{OLLAMA_MODEL}' not found.")
        print(f"  Pull it with: ollama pull {OLLAMA_MODEL}")
        print(f"  Or set OLLAMA_MODEL env var to one of the available models.")
        sys.exit(1)

    # Step 3: Send a simple prompt
    prompt = "In one sentence, what is the meaning of life?"
    print(f"Prompt: {prompt}")
    print()
    print("Generating response...")
    print("-" * 40)

    try:
        result = generate(prompt)
    except URLError as e:
        print(f"ERROR: Failed to generate response: {e}")
        sys.exit(1)
    except TimeoutError:
        print("ERROR: Request timed out (model may be loading or system is slow)")
        sys.exit(1)

    # Step 4: Display the response
    print()
    print("Response:")
    print(result.get("response", "(no response)").strip())
    print("-" * 40)
    print()

    # Step 5: Show timing information (the interesting part for learning)
    print("Timing Analysis:")
    print("-" * 40)

    total_ns = result.get("total_duration", 0)
    load_ns = result.get("load_duration", 0)
    prompt_eval_ns = result.get("prompt_eval_duration", 0)
    eval_ns = result.get("eval_duration", 0)

    prompt_tokens = result.get("prompt_eval_count", 0)
    gen_tokens = result.get("eval_count", 0)

    print(f"Total time:          {format_duration(total_ns)}")
    print(f"  Model load:        {format_duration(load_ns)}")
    print(f"  Prompt processing: {format_duration(prompt_eval_ns)} ({prompt_tokens} tokens)")
    print(f"  Generation:        {format_duration(eval_ns)} ({gen_tokens} tokens)")
    print()

    if prompt_eval_ns > 0:
        prompt_tps = calculate_tokens_per_second(prompt_tokens, prompt_eval_ns)
        print(f"Prompt throughput:   {prompt_tps:.1f} tokens/sec")

    if eval_ns > 0:
        gen_tps = calculate_tokens_per_second(gen_tokens, eval_ns)
        print(f"Generation speed:    {gen_tps:.1f} tokens/sec")

    print()
    print(f"Wall clock time:     {result.get('wall_clock_seconds', 0):.2f}s")
    print()

    # Step 6: Show the raw response format (educational)
    print("Raw API Response (for learning):")
    print("-" * 40)
    # Remove the response text to keep output manageable
    display_result = {k: v for k, v in result.items() if k != "response"}
    display_result["response"] = "(truncated for display)"
    print(json.dumps(display_result, indent=2))
    print()

    print("=" * 60)
    print("Hello World agent completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
