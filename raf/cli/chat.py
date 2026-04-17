import json
import os
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


def _print_question(question: str) -> None:
    print("\nQuestion:")
    print(f"- {question}")
    print("\nReply with your answer.")


def _merge_answers(goal: str, answers: str) -> str:
    return f"{goal}\n\nUser answers:\n{answers}"


def main() -> int:
    env_values = _load_env()
    adapter = _build_adapter(env_values)
    config = RafConfig()
    trace = TraceLogger()

    print("RAF Chat. Type 'exit' to quit.")
    while True:
        goal = input("\nYou: ").strip()
        if not goal:
            continue
        if goal.lower() in {"exit", "quit"}:
            break

        engine = RafEngine(config, adapter, trace)
        result = engine.run(goal)
        while result.get("metadata", {}).get("mode") == "clarify":
            questions = result["metadata"].get("questions", [])
            if not questions:
                break
            _print_question(questions[0])
            answer = input("\nYou: ").strip()
            if answer.lower() in {"exit", "quit"}:
                return 0
            goal = _merge_answers(goal, answer)
            engine = RafEngine(config, adapter, trace)
            result = engine.run(goal)

        print("\nRAF:")
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
