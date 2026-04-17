"""
raf.llm.groq_adapter
====================
Groq adapter using the OpenAI-compatible API.

Groq runs open-source models (Llama 3, Mixtral, Gemma) at very high speed
and offers a free tier — making it ideal for multi-model RAF ensembles
without cost.

Requires: pip install openai
API key:  https://console.groq.com  →  API Keys  →  Create API Key
Env var:  GROQ_API_KEY

Free-tier models (as of 2025):
  llama-3.3-70b-versatile   — best quality, recommended default
  llama-3.1-8b-instant      — fastest, good for jury seats
  mixtral-8x7b-32768        — strong reasoning
  gemma2-9b-it              — Google Gemma 2
"""

from typing import Any, Dict

from raf.llm.prompt_adapter import PromptBasedAdapter

# Models that support Groq's JSON mode (response_format=json_object).
# Mixtral does not — it falls back to prompt-only JSON enforcement.
_JSON_MODE_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "llama3-70b-8192",
    "llama3-8b-8192",
}


class GroqAdapter(PromptBasedAdapter):
    """Groq adapter — OpenAI-compatible, free tier available.

    Parameters
    ----------
    api_key:
        Groq API key (GROQ_API_KEY env var).
    model_name:
        Groq model ID.  Defaults to ``llama-3.3-70b-versatile``.
    temperature:
        Base temperature for agent-0.  Each subsequent agent index adds 0.1
        to encourage diverse proposals in a consortium.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "llama-3.3-70b-versatile",
        temperature: float = 0.2,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required for GroqAdapter: pip install openai"
            ) from exc

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model_name = model_name
        self.base_temperature = temperature

    def call_raw(self, task: str, payload: Dict[str, Any]) -> str:
        agent_index = payload.get("_agent_index", 0) if isinstance(payload, dict) else 0
        temperature = min(1.0, self.base_temperature + agent_index * 0.1)

        prompt = self._build_prompt(task, payload)

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 4096,
        }
        # Only enable JSON mode for models that support it
        if self.model_name in _JSON_MODE_MODELS:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
