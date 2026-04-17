import json
from typing import Any, Callable, Dict


class JsonParseError(ValueError):
    pass


class ModelCallError(RuntimeError):
    """Wraps any failure from call_json_with_repair with a machine-readable cause.

    Attributes
    ----------
    cause : str
        One of ``"api_error"`` (provider/network, model never ran),
        ``"parse_error"`` (model ran but output is not valid JSON), or
        ``"schema_error"`` (model ran and returned JSON but the shape is wrong).
    original : Exception
        The underlying exception that triggered this failure.
    """

    def __init__(self, cause: str, original: Exception) -> None:
        super().__init__(str(original))
        self.cause = cause
        self.original = original


def _find_balanced(text: str, open_char: str, close_char: str) -> str:
    start = text.find(open_char)
    if start == -1:
        return ""
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    candidate = _find_balanced(text, "{", "}")
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    candidate = _find_balanced(text, "[", "]")
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise JsonParseError("Failed to parse JSON")


def _classify_exc(api_raised: bool, exc: Exception) -> str:
    """Return the machine-readable cause string for a failed agent call.

    Parameters
    ----------
    api_raised:
        True when the exception came from ``adapter.call_raw()`` itself (i.e.
        the model was never reached or the provider returned an error).
    exc:
        The exception that terminated the call after all retries.
    """
    if api_raised:
        return "api_error"
    if isinstance(exc, JsonParseError):
        return "parse_error"
    # ValueError (from validators), KeyError, TypeError, etc. → wrong output shape
    return "schema_error"


def call_json_with_repair(
    adapter,
    task: str,
    payload: Dict[str, Any],
    validator: Callable[[Dict[str, Any]], Dict[str, Any]],
    retry_limit: int,
) -> Dict[str, Any]:
    api_raised = True  # will be set False once the first call_raw succeeds
    try:
        raw = adapter.call_raw(task, payload)
    except Exception as exc:
        raise ModelCallError("api_error", exc) from exc
    api_raised = False
    attempts = 0

    while True:
        try:
            parsed = parse_json(raw)
            if not isinstance(parsed, dict):
                raise JsonParseError("Expected JSON object")
            return validator(parsed)
        except Exception as exc:
            if attempts >= retry_limit:
                cause = _classify_exc(False, exc)
                raise ModelCallError(cause, exc) from exc
            try:
                raw = adapter.call_raw(
                    "repair",
                    {
                        "task": task,
                        "task_payload": payload,
                        "error": str(exc),
                        "last_raw": raw,
                    },
                )
            except Exception as repair_exc:
                raise ModelCallError("api_error", repair_exc) from repair_exc
            attempts += 1


def call_json_with_guard(
    adapter,
    task: str,
    payload: Dict[str, Any],
    validator: Callable[[Dict[str, Any]], Dict[str, Any]],
    retry_limit: int,
    guard: Callable[[Dict[str, Any]], None],
) -> Dict[str, Any]:
    try:
        raw = adapter.call_raw(task, payload)
    except Exception as exc:
        raise ModelCallError("api_error", exc) from exc
    attempts = 0

    while True:
        try:
            parsed = parse_json(raw)
            if not isinstance(parsed, dict):
                raise JsonParseError("Expected JSON object")
            validated = validator(parsed)
            guard(validated)
            return validated
        except Exception as exc:
            if attempts >= retry_limit:
                cause = _classify_exc(False, exc)
                raise ModelCallError(cause, exc) from exc
            try:
                raw = adapter.call_raw(
                    "repair",
                    {
                        "task": task,
                        "task_payload": payload,
                        "error": str(exc),
                        "last_raw": raw,
                    },
                )
            except Exception as repair_exc:
                raise ModelCallError("api_error", repair_exc) from repair_exc
            attempts += 1
