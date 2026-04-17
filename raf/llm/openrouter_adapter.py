"""
raf.llm.openrouter_adapter
==========================
OpenRouter adapter — access hundreds of models via a single OpenAI-compatible endpoint.
API key loaded from OPENROUTER_API_KEY env var (set in .env, loaded by python-dotenv).

Requires: pip install openai
API key:  https://openrouter.ai/keys

Reasoning models (extra_body={"reasoning":{"enabled":True}}):
  qwen/qwen3-next-80b-a3b-instruct:free    — Qwen 3 80B MoE reasoning (default)
  nvidia/nemotron-3-super-120b-a12b:free   — large NVIDIA reasoning model
  nvidia/nemotron-nano-12b-v2-vl:free      — small NVIDIA reasoning model (vision capable)
  qwen/qwen3-next-80b-a3b-instruct:free    — Qwen 3 80B MoE reasoning
  qwen/qwen3-coder:free                    — Qwen 3 coder, reasoning
  liquid/lfm-2.5-1.2b-thinking:free        — tiny thinking model
  z-ai/glm-5.1                             — GLM 5.1 with reasoning
  google/gemma-4-26b-a4b-it:free           — Gemma 4 26B IT (free)
  qwen/qwen3.6-plus                        — Qwen 3.6 Plus
  openai/gpt-5.4-nano                      — GPT-5.4 Nano
  qwen/qwen3.5-9b                          — Qwen 3.5 9B
  qwen/qwen3.5-35b-a3b                     — Qwen 3.5 35B A3B
  openai/gpt-oss-120b:free                 — GPT OSS 120B (free, reasoning)

JSON-mode models (response_format=json_object confirmed):
  arcee-ai/trinity-large-preview:free      — Arcee Trinity Large

Prompt-only JSON (no special flags, repair loop handles compliance):
  z-ai/glm-4.5-air:free                    — GLM-4.5 Air
  mistralai/devstral-2512                  — Devstral (coding-focused)
  mistralai/ministral-14b-2512             — Ministral 14B (vision-capable, text used in RAF)
  meta-llama/llama-3.2-3b-instruct:free    — LLaMA 3.2 3B (tiny, fast leaf proposer)
  mistralai/mistral-nemo                   — Mistral Nemo (mid-size general proposer)
"""

from typing import Any, Dict

from raf.llm.prompt_adapter import PromptBasedAdapter

# Models that reliably support OpenAI JSON mode via OpenRouter.
# Verified against live OpenRouter API (March 2026) — models NOT in this set fall back
# to prompt-only JSON compliance enforced by json_utils repair.
_JSON_MODE_MODELS = {
    "arcee-ai/trinity-large-preview:free",   # response_format confirmed
}

# Models that support OpenRouter's reasoning extension.
# Passing extra_body={"reasoning": {"enabled": True}} lets the model think
# before answering — reasoning tokens are hidden from response content
# so JSON output is unaffected.
_REASONING_MODELS = {
    # stepfun/step-3.5-flash:free removed — 404 "No endpoints found" on OpenRouter
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "qwen/qwen3-coder:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
    # New reasoning models (extra_body={"reasoning":{"enabled":True}})
    "z-ai/glm-5.1",
    "google/gemma-4-26b-a4b-it:free",
    "qwen/qwen3.6-plus",
    "openai/gpt-5.4-nano",
    "qwen/qwen3.5-9b",
    "qwen/qwen3.5-35b-a3b",
    "moonshotai/kimi-k2-thinking",
    "x-ai/grok-4.1-fast",
    "openai/gpt-oss-120b:free",
}


class OpenRouterAdapter(PromptBasedAdapter):
    """OpenRouter adapter — hundreds of models via one OpenAI-compatible key.

    Parameters
    ----------
    api_key:
        OpenRouter API key (``OPENROUTER_API_KEY`` env var).
    model_name:
        OpenRouter model ID, e.g. ``"meta-llama/llama-3.3-70b-instruct:free"``.
        Append ``:free`` to use the free tier for supported models.
    temperature:
        Base temperature for agent-0.  Each subsequent consortium agent index
        adds 0.1 to encourage diverse proposals.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "qwen/qwen3-next-80b-a3b-instruct:free",
        temperature: float = 0.2,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required for OpenRouterAdapter: pip install openai"
            ) from exc

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
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
        # Enable JSON mode only for models known to support it via OpenRouter.
        if self.model_name in _JSON_MODE_MODELS:
            kwargs["response_format"] = {"type": "json_object"}

        # Enable reasoning for models that support it — the reasoning tokens are
        # hidden from response content so JSON output is unaffected.
        if self.model_name in _REASONING_MODELS:
            kwargs["extra_body"] = {"reasoning": {"enabled": True}}

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        # Report actual token counts from OpenRouter usage metadata.
        usage = getattr(response, "usage", None)
        if usage is not None:
            tokens_in = getattr(usage, "prompt_tokens", None) or len(prompt) // 4
            tokens_out = getattr(usage, "completion_tokens", None) or len(content) // 4
        else:
            tokens_in = len(prompt) // 4
            tokens_out = len(content) // 4
        self._report_usage(tokens_in, tokens_out)
        return content
