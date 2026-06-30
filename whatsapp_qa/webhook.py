"""Receptor de webhook para os providers oficiais (Cloud API e Twilio).

As respostas do bot sob teste chegam aqui (o WhatsApp/Twilio entrega via HTTP) e
sao gravadas na inbox JSONL que o provider le. Usa apenas a biblioteca padrao.

Uso:
    python -m whatsapp_qa.webhook --port 8080 [--verify-token SEU_TOKEN]

Exponha esta porta publicamente (ex.: ngrok / tunel reverso) e configure a URL
no painel da Meta (Cloud API) ou no numero da Twilio. Apenas as mensagens
recebidas DO numero do bot importam para o teste.

Endpoints:
    GET  /webhook  - verificacao de assinatura da Cloud API (hub.challenge)
    POST /webhook  - eventos: Cloud API (JSON) ou Twilio (form-urlencoded)
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import Config
from .providers.inbox import append_inbound


def _extract_cloud_texts(payload: dict) -> list[str]:
    """Extrai textos de mensagens recebidas de um payload da Cloud API."""
    texts: list[str] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") == "text":
                    body = msg.get("text", {}).get("body")
                    if body:
                        texts.append(body)
    return texts


def make_handler(config: Config, verify_token: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silencia log padrao ruidoso
            pass

        def _ok(self, code: int = 200, body: bytes = b"OK") -> None:
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # verificacao da Cloud API
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            mode = qs.get("hub.mode", [""])[0]
            token = qs.get("hub.verify_token", [""])[0]
            challenge = qs.get("hub.challenge", [""])[0]
            if mode == "subscribe" and token == verify_token:
                self._ok(200, challenge.encode("utf-8"))
            else:
                self._ok(403, b"forbidden")

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b""
            ctype = self.headers.get("Content-Type", "")
            texts: list[str] = []

            if "application/json" in ctype:
                try:
                    texts = _extract_cloud_texts(json.loads(raw.decode("utf-8")))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    texts = []
            else:  # Twilio envia form-urlencoded com o campo Body
                form = urllib.parse.parse_qs(raw.decode("utf-8", errors="replace"))
                body = form.get("Body", [""])[0]
                if body:
                    texts = [body]

            now = time.time()
            for t in texts:
                append_inbound(config.inbox_path, t, now, raw={"source": "webhook"})
            self._ok()

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Receptor de webhook do harness de WhatsApp.")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--verify-token", default="waqa-verify")
    args = parser.parse_args(argv)

    config = Config.from_env()
    handler = make_handler(config, args.verify_token)
    server = HTTPServer((args.host, args.port), handler)
    print(f"Webhook ouvindo em http://{args.host}:{args.port}/webhook "
          f"(inbox: {config.inbox_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando webhook.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
