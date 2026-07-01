"""Receptor de webhook para captar as respostas do bot sob teste.

As respostas chegam aqui (o gateway/WhatsApp entrega via HTTP) e sao gravadas na
inbox JSONL que o provider le. Usa apenas a biblioteca padrao.

Uso:
    WAQA_VERIFY_TOKEN=... python -m whatsapp_qa.webhook --port 8080

Exponha a porta publicamente (ex.: ngrok) e configure a URL no painel do gateway
(Cloud API, Twilio ou o gateway proprio). Apenas as mensagens recebidas DO numero
do bot importam para o teste.

Seguranca:
    - GET  /webhook: verificacao da Cloud API (hub.challenge) exige --verify-token
      ou WAQA_VERIFY_TOKEN (sem default publico).
    - POST /webhook: se WAQA_WEBHOOK_SECRET estiver definido, o POST e autenticado
      por HMAC (X-Hub-Signature-256, padrao Meta) ou por header estatico
      X-Webhook-Token; caso contrario e rejeitado. Sem segredo definido, o
      receptor aceita mas AVISA no start (recomendado definir o segredo).
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import Config
from .providers.inbox import append_inbound
from .providers.paths import get_path_all


def _is_truthy(v) -> bool:
    return v in (True, "true", "True", 1, "1")


def _digits(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _sender_matches(sender, tgt_digits: str) -> bool:
    """Compara remetente (JID/E.164/puro) com o numero alvo por sufixo de digitos."""
    d = _digits(sender)
    if not d or not tgt_digits:
        return True  # sem dados para comparar -> nao filtra
    return d.endswith(tgt_digits) or tgt_digits.endswith(d)


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


def _extract_generic_texts(payload, config: Config) -> list[str]:
    """Extrai TODOS os textos recebidos pelos caminhos configurados.

    - Coleta multipla via wildcard (varias bolhas num unico POST).
    - Ignora ecos das proprias mensagens (flag fromMe), pareando por posicao.
    - Se o remetente e o numero-alvo estao disponiveis, descarta mensagens de
      outros remetentes (normalizando JID '...@s.whatsapp.net'/'whatsapp:').
    """
    raw_texts = get_path_all(payload, config.generic_inbound_text_path)
    if not raw_texts:
        return []
    n = len(raw_texts)

    flags = (get_path_all(payload, config.generic_inbound_fromme_path)
             if config.generic_inbound_fromme_path else [])
    senders = (get_path_all(payload, config.generic_inbound_from_path)
               if (config.generic_inbound_from_path and config.target_number) else [])
    tgt = _digits(config.target_number) if config.target_number else ""

    # Alinha por posicao apenas quando o wildcard produziu a mesma cardinalidade.
    aligned_flags = flags if len(flags) == n else None
    aligned_senders = senders if len(senders) == n else None

    out: list[str] = []
    for i, t in enumerate(raw_texts):
        if t in (None, ""):
            continue
        if aligned_flags is not None and _is_truthy(aligned_flags[i]):
            continue
        if aligned_senders is not None and tgt and not _sender_matches(aligned_senders[i], tgt):
            continue
        out.append(str(t))

    # Fallbacks para payloads de mensagem unica com listas desalinhadas.
    if aligned_flags is None and flags and n == 1 and any(_is_truthy(f) for f in flags):
        return []
    if aligned_senders is None and senders and tgt and not any(_sender_matches(s, tgt) for s in senders):
        return []
    return out


def extract_texts(payload, config: Config, content_type: str) -> list[str]:
    """Decide como extrair o(s) texto(s) recebido(s) conforme o provider/config."""
    if config.generic_inbound_text_path:  # provider generico configurado tem prioridade
        return _extract_generic_texts(payload, config)
    if isinstance(payload, dict) and "entry" in payload:
        return _extract_cloud_texts(payload)
    return []


def authenticate_post(config: Config, headers, raw: bytes) -> bool:
    """Autentica o POST do webhook quando WAQA_WEBHOOK_SECRET esta definido."""
    secret = config.webhook_secret
    if not secret:
        return True  # sem segredo configurado (aceita; avisado no start)
    sig = headers.get("X-Hub-Signature-256", "")
    if sig.startswith("sha256="):
        expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    token = headers.get("X-Webhook-Token", "")
    if token:
        return hmac.compare_digest(token, secret)
    return False


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
            if mode == "subscribe" and hmac.compare_digest(token, verify_token):
                self._ok(200, challenge.encode("utf-8"))
            else:
                self._ok(403, b"forbidden")

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b""

            if not authenticate_post(config, self.headers, raw):
                self._ok(403, b"forbidden")
                return

            ctype = self.headers.get("Content-Type", "")
            texts: list[str] = []
            if "application/json" in ctype:
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    texts = extract_texts(payload, config, ctype)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    texts = []
            else:  # Twilio (ou gateway) form-urlencoded com o campo Body
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
    parser.add_argument("--verify-token", default="", help="Token de verificacao (ou WAQA_VERIFY_TOKEN).")
    args = parser.parse_args(argv)

    verify_token = args.verify_token or os.environ.get("WAQA_VERIFY_TOKEN", "")
    if not verify_token:
        print("Erro: defina --verify-token ou WAQA_VERIFY_TOKEN (sem default publico).",
              file=sys.stderr)
        return 2

    config = Config.from_env()
    if not config.webhook_secret:
        print("AVISO: WAQA_WEBHOOK_SECRET nao definido - o POST /webhook NAO sera autenticado. "
              "Defina um segredo para producao.", file=sys.stderr)

    handler = make_handler(config, verify_token)
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
