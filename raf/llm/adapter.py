from typing import Any, Callable, Dict, Optional


class ModelAdapter:
    def __init__(self) -> None:
        # Optional hook set by RafEngine so adapters can report (tokens_in, tokens_out)
        # back to the engine's budget counter after every API call.
        # Never set directly — always assigned via RafEngine._wire_usage_callbacks().
        self._usage_callback: Optional[Callable[[int, int], None]] = None

    def _report_usage(self, tokens_in: int, tokens_out: int) -> None:
        """Fire the usage callback if one is registered.

        Subclasses call this at the end of every ``call_raw`` implementation,
        passing either actual token counts (when the API returns them) or rough
        estimates (``len(prompt) // 4``) as a fallback.
        """
        if self._usage_callback:
            self._usage_callback(tokens_in, tokens_out)

    def call_raw(self, task: str, payload: Dict[str, Any]) -> str:
        raise NotImplementedError
