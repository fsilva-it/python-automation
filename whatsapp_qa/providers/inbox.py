"""Inbox em arquivo (JSONL) compartilhada entre o webhook e os providers reais.

Os providers oficiais (Cloud API, Twilio) nao recebem a resposta de forma
sincrona: o bot responde e o WhatsApp entrega a mensagem ao webhook. O receptor
de webhook (webhook.py) anexa cada mensagem recebida como uma linha JSON neste
arquivo; os providers leem dele em fetch_since.
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import InboundMessage


def append_inbound(inbox_path: str, text: str, timestamp: float, raw: dict | None = None) -> None:
    line = json.dumps({"text": text, "timestamp": timestamp, "raw": raw}, ensure_ascii=False)
    with open(inbox_path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_since(inbox_path: str, since: float) -> list[InboundMessage]:
    p = Path(inbox_path)
    if not p.exists():
        return []
    out: list[InboundMessage] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = float(rec.get("timestamp", 0))
        if ts > since:
            out.append(InboundMessage(text=str(rec.get("text", "")), timestamp=ts, raw=rec.get("raw")))
    return out
