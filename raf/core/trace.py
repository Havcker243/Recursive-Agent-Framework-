import json
import sys
import time
from typing import Any, Dict


from typing import Callable, List, Optional


class TraceLogger:
    def __init__(self, emit: Optional[Callable[[Dict[str, Any]], None]] = None, store: bool = False, quiet: bool = False) -> None:
        self._spinner = ["|", "/", "-", "\\"]
        self._spin_index = 0
        self._last_len = 0
        self._emit = emit
        self._store = store
        self._quiet = quiet  # suppress stdout JSON dump (useful when events stream over WebSocket)
        self._events: List[Dict[str, Any]] = []

    def events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def log(self, event: Dict[str, Any]) -> None:
        event = dict(event)
        event["timestamp"] = time.time()
        if self._store:
            self._events.append(event)
        if self._emit:
            self._emit(event)
        if not self._quiet:
            print(json.dumps(event))
        status = event.get("status")
        node_id = event.get("node_id")
        depth = event.get("depth")
        if not status or node_id is None:
            return

        parts = [f"[{node_id} depth={depth}] {status}"]
        if "winner" in event:
            parts.append(f"winner={event['winner']}")
        if "confidence" in event:
            parts.append(f"conf={event['confidence']}")
        if "retries" in event:
            parts.append(f"retries={event['retries']}")
        if "order" in event:
            parts.append(f"order={event['order']}")
        if "error" in event:
            parts.append(f"error={event['error']}")
        line = " | ".join(parts)
        if not sys.stderr.isatty():
            return
        spin = self._spinner[self._spin_index % len(self._spinner)]
        self._spin_index += 1
        out = f"{spin} {line}"
        pad = " " * max(0, self._last_len - len(out))
        sys.stderr.write("\r" + out + pad)
        sys.stderr.flush()
        self._last_len = len(out)
        if status in {"DONE", "FAILED"}:
            sys.stderr.write("\n")
