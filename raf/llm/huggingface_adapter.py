from typing import Any, Dict

from raf.llm.prompt_adapter import PromptBasedAdapter


class HuggingFaceAdapter(PromptBasedAdapter):
    """HuggingFace Inference API adapter. Requires: pip install requests
    Works with any model that supports the chat completions endpoint,
    e.g. meta-llama/Llama-3.1-70B-Instruct, mistralai/Mixtral-8x7B-Instruct-v0.1
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "meta-llama/Llama-3.1-70B-Instruct",
        temperature: float = 0.2,
    ) -> None:
        try:
            import requests as _req  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("requests is required for HuggingFaceAdapter: pip install requests") from exc

        self.api_key = api_key
        self.model_name = model_name
        self.base_temperature = temperature
        self.url = (
            f"https://api-inference.huggingface.co/models/{model_name}/v1/chat/completions"
        )

    def call_raw(self, task: str, payload: Dict[str, Any]) -> str:
        import requests

        agent_index = payload.get("_agent_index", 0) if isinstance(payload, dict) else 0
        temperature = min(1.0, self.base_temperature + agent_index * 0.2)

        prompt = self._build_prompt(task, payload)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 4096,
        }
        response = requests.post(self.url, json=body, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"] or ""
