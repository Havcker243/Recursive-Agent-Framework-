from typing import Any, Dict

from raf.llm.prompt_adapter import PromptBasedAdapter


class ClaudeAdapter(PromptBasedAdapter):
    """Anthropic Claude adapter. Requires: pip install anthropic"""

    def __init__(self, api_key: str, model_name: str = "claude-opus-4-6", temperature: float = 0.2) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic is required for ClaudeAdapter: pip install anthropic") from exc

        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name
        self.base_temperature = temperature

    def call_raw(self, task: str, payload: Dict[str, Any]) -> str:
        agent_index = payload.get("_agent_index", 0) if isinstance(payload, dict) else 0
        temperature = min(1.0, self.base_temperature + agent_index * 0.2)

        prompt = self._build_prompt(task, payload)
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text if response.content else ""
