"""Tool implementations for RAF base-case execution.

Tools are opt-in via RafConfig.tools_enabled and RafConfig.available_tools.
The LLM can request a tool by including {"tool_call": {"name": "...", "args": {...}}}
in its base_execute response.
"""

import re
import subprocess
import textwrap
from typing import Any, Dict
from urllib.parse import urlparse


def _web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo HTML (no API key required)."""
    try:
        import requests
        from html.parser import HTMLParser

        class _ResultParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results: list[str] = []
                self._in_result = False
                self._text = ""

            def handle_starttag(self, tag, attrs):
                attr_dict = dict(attrs)
                if tag == "a" and "result__a" in attr_dict.get("class", ""):
                    self._in_result = True
                    self._text = ""

            def handle_endtag(self, tag):
                if tag == "a" and self._in_result:
                    if self._text.strip():
                        self.results.append(self._text.strip())
                    self._in_result = False

            def handle_data(self, data):
                if self._in_result:
                    self._text += data

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; RAF-tool/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        }
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        parser = _ResultParser()
        parser.feed(resp.text)
        snippets = parser.results[:max_results]

        if not snippets:
            # Fallback: grab raw text snippets from the page
            import re
            found = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            snippets = [re.sub(r"<[^>]+>", "", s).strip() for s in found[:max_results]]

        return "\n".join(f"{i+1}. {s}" for i, s in enumerate(snippets)) or "No results found."

    except Exception as exc:
        return f"web_search failed: {exc}"


# Patterns that are stripped of spaces and lowercased before matching.
# This list blocks the most common code-execution and exfiltration vectors but
# is NOT a full sandbox — run_python is excluded from available_tools by default.
_BLOCKED_PYTHON_PATTERNS = [
    # stdlib imports that give filesystem / process / network access
    "import os", "import sys", "import subprocess", "import shutil",
    "import socket", "import pathlib", "import importlib", "import ctypes",
    "import pickle", "import marshal", "import tempfile", "import multiprocessing",
    # dynamic import builtins
    "__import__", "builtins", "__builtins__",
    # introspection escapes (MRO-walk exploit)
    "__class__", "__subclasses__", "__globals__", "__mro__",
    # generic code execution
    "open(", "exec(", "eval(", "compile(",
    # attribute / reflection access
    "getattr(", "setattr(", "globals(", "locals(", "vars(",
    # os-level calls
    "os.system", "os.popen", "os.exec", "os.spawn",
]

# Regex for private/loopback IP ranges and localhost — used to block SSRF in http_get.
_PRIVATE_HOST_RE = re.compile(
    r"^(localhost"
    r"|127\.\d+\.\d+\.\d+"
    r"|10\.\d+\.\d+\.\d+"
    r"|192\.168\.\d+\.\d+"
    r"|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+"
    r"|::1"
    r"|0\.0\.0\.0"
    r")$",
    re.IGNORECASE,
)


def _run_python(code: str, timeout: int = 10) -> str:
    """Execute Python code in a subprocess with a timeout.

    WARNING: This is NOT a full sandbox. It blocks the most obvious abuse
    patterns via a deny-list but cannot stop all adversarial code.
    Only enable tools_enabled=true in a trusted, isolated environment.
    """
    code_lower = code.lower().replace(" ", "")
    for pattern in _BLOCKED_PYTHON_PATTERNS:
        if pattern.replace(" ", "").lower() in code_lower:
            return f"run_python blocked: forbidden pattern ({pattern!r})"
    safe_code = textwrap.dedent(code)
    try:
        result = subprocess.run(
            ["python", "-c", safe_code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            output += f"\nError: {result.stderr.strip()[:500]}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"run_python timed out after {timeout}s"
    except Exception as exc:
        return f"run_python failed: {exc}"


def _http_get(url: str, timeout: int = 10) -> str:
    """Perform an HTTP GET and return the first 2000 chars of the response text.

    Private/loopback addresses are blocked to prevent SSRF.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return "http_get blocked: only http/https URLs are allowed"
        hostname = (parsed.hostname or "").lower()
        if _PRIVATE_HOST_RE.match(hostname):
            return "http_get blocked: private/loopback addresses are not allowed"
        import requests
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "RAF-tool/1.0"})
        resp.raise_for_status()
        return resp.text[:2000]
    except Exception as exc:
        return f"http_get failed: {exc}"


_TOOL_REGISTRY: Dict[str, Any] = {
    "web_search": lambda args: _web_search(
        args.get("query", ""),
        max_results=int(args.get("max_results", 5)),
    ),
    "run_python": lambda args: _run_python(
        args.get("code", ""),
        timeout=int(args.get("timeout", 10)),
    ),
    "http_get": lambda args: _http_get(
        args.get("url", ""),
        timeout=int(args.get("timeout", 10)),
    ),
}


def execute_tool(name: str, args: Dict[str, Any]) -> str:
    """Execute a registered tool by name. Returns a string result."""
    fn = _TOOL_REGISTRY.get(name)
    if fn is None:
        return f"Unknown tool: {name}. Available: {list(_TOOL_REGISTRY)}"
    return fn(args)


def available_tool_schemas() -> str:
    """Return a description of available tools for injection into LLM prompts."""
    return (
        "Available tools (include tool_call in your response to use one):\n"
        '- web_search: {"name":"web_search","args":{"query":"string","max_results":5}}\n'
        '- run_python: {"name":"run_python","args":{"code":"string","timeout":10}}\n'
        '- http_get:   {"name":"http_get","args":{"url":"string","timeout":10}}\n'
    )
