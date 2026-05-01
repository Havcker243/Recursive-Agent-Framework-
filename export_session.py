"""
Convert a Claude Code .jsonl session file to a clean markdown document.
Usage: python export_session.py <session.jsonl> <output.md>
"""
import json
import sys
from datetime import datetime


def extract_text(content):
    """Extract plain text from a message content field (str or list)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block["text"].strip())
                elif block.get("type") == "tool_result":
                    inner = block.get("content", "")
                    if isinstance(inner, list):
                        for item in inner:
                            if isinstance(item, dict) and item.get("type") == "text":
                                parts.append(f"```\n{item['text'].strip()}\n```")
                    elif isinstance(inner, str) and inner.strip():
                        parts.append(f"```\n{inner.strip()}\n```")
        return "\n\n".join(parts)
    return ""


def format_timestamp(ts):
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return ts


def convert(jsonl_path, output_path):
    messages = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")

            if msg_type == "user":
                content = obj.get("message", {}).get("content", "")
                # Skip pure tool-result messages (internal plumbing, not user input)
                if isinstance(content, list) and all(
                    isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in content
                    if isinstance(b, dict)
                ):
                    # Extract agent/tool output and label it separately
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        inner = block.get("content", "")
                        if isinstance(inner, list):
                            for item in inner:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    t = item["text"].strip()
                                    if t:
                                        messages.append({
                                            "role": "agent",
                                            "text": t,
                                            "timestamp": obj.get("timestamp", ""),
                                        })
                        elif isinstance(inner, str) and inner.strip():
                            messages.append({
                                "role": "agent",
                                "text": inner.strip(),
                                "timestamp": obj.get("timestamp", ""),
                            })
                    continue

                text = extract_text(content)
                if text:
                    messages.append({
                        "role": "user",
                        "text": text,
                        "timestamp": obj.get("timestamp", ""),
                    })

            elif msg_type == "assistant":
                content = obj.get("message", {}).get("content", [])
                if isinstance(content, list):
                    text_blocks = [
                        b["text"].strip()
                        for b in content
                        if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip()
                    ]
                    text = "\n\n".join(text_blocks)
                    if text:
                        messages.append({
                            "role": "assistant",
                            "text": text,
                            "timestamp": obj.get("timestamp", ""),
                        })

    if not messages:
        print("No messages found — check the file path.")
        return

    # Deduplicate consecutive same-role messages (Claude Code sometimes splits one turn)
    deduped = []
    for msg in messages:
        if deduped and deduped[-1]["role"] == msg["role"] and msg["role"] != "agent":
            deduped[-1]["text"] += "\n\n" + msg["text"]
        else:
            deduped.append(msg)

    # Write markdown
    with open(output_path, "w", encoding="utf-8") as out:
        out.write("# Claude Code Session — Recursive Agent Framework\n\n")
        if deduped:
            out.write(f"*{format_timestamp(deduped[0]['timestamp'])}*\n\n")
        out.write("---\n\n")

        for msg in deduped:
            if msg["role"] == "user":
                out.write(f"## You\n\n{msg['text']}\n\n")
            elif msg["role"] == "agent":
                out.write(f"## Subagent Output\n\n{msg['text']}\n\n")
            else:
                out.write(f"## Claude\n\n{msg['text']}\n\n")
            out.write("---\n\n")

    print(f"Exported {len(deduped)} messages to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python export_session.py <session.jsonl> <output.md>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
