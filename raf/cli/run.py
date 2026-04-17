import json
import os
import sys
from pathlib import Path

from raf.core.engine import RafEngine
from raf.core.trace import TraceLogger
from raf.llm.gemini_adapter import GeminiAdapter
from raf.llm.mock_adapter import MockAdapter
from raf.schemas import RafConfig


def _load_env() -> dict:
    values: dict[str, str] = {}
    candidates = [Path("raf") / ".env", Path(".env")]
    env_path = next((path for path in candidates if path.exists()), None)
    if not env_path:
        return values

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'").strip()
        values[key] = value
        os.environ.setdefault(key, value)
    return values


def _build_adapter(env_values: dict) -> object:
    llm = env_values.get("RAF_LLM") or os.getenv("RAF_LLM", "gemini")
    llm = llm.lower()
    if llm == "gemini":
        api_key = env_values.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini adapter")
        model_name = env_values.get("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        temperature = float(env_values.get("GEMINI_TEMPERATURE") or os.getenv("GEMINI_TEMPERATURE", "0.2"))
        return GeminiAdapter(api_key=api_key, model_name=model_name, temperature=temperature)
    return MockAdapter()


def _parse_args(argv: list) -> tuple:
    """Returns (goal, jury_model). Handles optional --jury-model MODEL flag."""
    args = argv[1:]
    jury_model = None
    filtered = []
    i = 0
    while i < len(args):
        if args[i] == "--jury-model" and i + 1 < len(args):
            jury_model = args[i + 1]
            i += 2
        else:
            filtered.append(args[i])
            i += 1
    goal = " ".join(filtered)
    return goal, jury_model


def main() -> int:
    goal, jury_model = _parse_args(sys.argv)
    if not goal:
        print("Usage: python -m raf.cli.run [--jury-model MODEL] \"your goal\"")
        return 1

    env_values = _load_env()
    config = RafConfig()
    consortium_adapter = _build_adapter(env_values)

    jury_adapter = None
    if jury_model:
        api_key = env_values.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required to use --jury-model")
        temperature = float(env_values.get("GEMINI_TEMPERATURE") or os.getenv("GEMINI_TEMPERATURE", "0.2"))
        jury_adapter = GeminiAdapter(api_key=api_key, model_name=jury_model, temperature=temperature)

    trace = TraceLogger()
    engine = RafEngine(config, consortium_adapter, trace, jury_adapter=jury_adapter)
    result = engine.run(goal)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
