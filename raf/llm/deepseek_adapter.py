from typing import Any, Dict

from raf.llm.prompt_adapter import PromptBasedAdapter


class DeepSeekAdapter(PromptBasedAdapter):
    """DeepSeek adapter using OpenAI-compatible API. Requires: pip install openai"""

    def __init__(self, api_key: str, model_name: str = "deepseek-chat", temperature: float = 0.2) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is required for DeepSeekAdapter: pip install openai") from exc

        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model_name = model_name
        self.base_temperature = temperature

    def call_raw(self, task: str, payload: Dict[str, Any]) -> str:
        agent_index = payload.get("_agent_index", 0) if isinstance(payload, dict) else 0
        temperature = min(1.0, self.base_temperature + agent_index * 0.2)

        prompt = self._build_prompt(task, payload)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""
