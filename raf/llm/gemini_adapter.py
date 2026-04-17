from typing import Any, Dict

from raf.llm.prompt_adapter import PromptBasedAdapter


class GeminiAdapter(PromptBasedAdapter):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro", temperature: float = 0.2) -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai is required for GeminiAdapter: pip install google-genai") from exc

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.base_temperature = temperature

    def call_raw(self, task: str, payload: Dict[str, Any]) -> str:
        from google.genai import types

        # Vary temperature per agent index so consortium proposals are diverse
        agent_index = payload.get("_agent_index", 0) if isinstance(payload, dict) else 0
        temperature = min(1.0, self.base_temperature + agent_index * 0.2)

        prompt = self._build_prompt(task, payload)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        # Report actual token counts when available; fall back to char-length estimate.
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            tokens_in = getattr(usage, "prompt_token_count", None) or len(prompt) // 4
            tokens_out = getattr(usage, "candidates_token_count", None) or len(response.text or "") // 4
        else:
            tokens_in = len(prompt) // 4
            tokens_out = len(response.text or "") // 4
        self._report_usage(tokens_in, tokens_out)
        return response.text or ""
