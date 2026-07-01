"""Configuracao do harness, lida de variaveis de ambiente.

Nenhum segredo fica no codigo. Defina via ambiente (ou um arquivo .env carregado
pelo seu shell). Veja whatsapp_qa/README.md para a lista completa.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Parametros de execucao resolvidos a partir do ambiente."""

    # Qual camada de transporte usar: "mock" | "cloud" | "twilio".
    provider: str = "mock"

    # Numero do bot/assistente que sera testado (formato E.164, ex: 5511999999999).
    target_number: str = ""

    # Como avaliar a resposta: "keyword" | "ai" | "exact" | "hybrid".
    grader: str = "hybrid"

    # Tempo maximo de espera (segundos) pela resposta do bot a cada mensagem.
    reply_timeout: float = 30.0

    # Pausa entre casos de teste (segundos) - evita rate limit e respeita ordem.
    pause_between: float = 2.0

    # --- WhatsApp Cloud API (Meta) ---
    cloud_phone_number_id: str = ""
    cloud_access_token: str = ""
    cloud_api_version: str = "v21.0"

    # --- Twilio ---
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from: str = ""  # ex: "whatsapp:+14155238886"

    # --- Avaliacao por IA (Claude) ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # --- Provider generico (gateway/BSP proprio, ex: Evolution, Z-API, 360dialog) ---
    # Preset opcional que preenche defaults conhecidos (ver providers/presets.py).
    generic_preset: str = ""
    generic_send_url: str = ""
    generic_method: str = "POST"
    generic_content_type: str = "json"  # "json" ou "form"
    generic_auth_type: str = "bearer"   # bearer | header | query | basic | none
    generic_auth_header: str = "Authorization"
    generic_auth_query_param: str = "token"
    generic_auth_token: str = ""
    generic_headers_json: str = ""      # headers estaticos extras, como JSON
    generic_body_template: str = ""     # JSON de envio com {{to}} e {{body}}
    generic_msg_id_path: str = ""       # caminho ate o id na resposta de envio
    # Webhook (mensagens recebidas):
    generic_inbound_text_path: str = ""   # caminho ate o texto recebido
    generic_inbound_from_path: str = ""   # caminho ate o remetente
    generic_inbound_fromme_path: str = ""  # caminho ate flag "enviado por nos" (para ignorar ecos)

    # Arquivo onde o receptor de webhook grava as mensagens recebidas (inbox).
    inbox_path: str = "whatsapp_qa_inbox.jsonl"

    @classmethod
    def from_env(cls) -> "Config":
        def env(name: str, default: str) -> str:
            return os.environ.get(name, default)

        return cls(
            provider=env("WAQA_PROVIDER", "mock"),
            target_number=env("WAQA_TARGET_NUMBER", ""),
            grader=env("WAQA_GRADER", "hybrid"),
            reply_timeout=float(env("WAQA_REPLY_TIMEOUT", "30")),
            pause_between=float(env("WAQA_PAUSE_BETWEEN", "2")),
            cloud_phone_number_id=env("WAQA_CLOUD_PHONE_NUMBER_ID", ""),
            cloud_access_token=env("WAQA_CLOUD_ACCESS_TOKEN", ""),
            cloud_api_version=env("WAQA_CLOUD_API_VERSION", "v21.0"),
            twilio_account_sid=env("WAQA_TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=env("WAQA_TWILIO_AUTH_TOKEN", ""),
            twilio_from=env("WAQA_TWILIO_FROM", ""),
            # Reaproveita ANTHROPIC_API_KEY se ja existir no ambiente.
            anthropic_api_key=env("WAQA_ANTHROPIC_API_KEY", env("ANTHROPIC_API_KEY", "")),
            anthropic_model=env("WAQA_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            generic_preset=env("WAQA_GENERIC_PRESET", ""),
            generic_send_url=env("WAQA_GENERIC_SEND_URL", ""),
            generic_method=env("WAQA_GENERIC_METHOD", "POST"),
            generic_content_type=env("WAQA_GENERIC_CONTENT_TYPE", "json"),
            generic_auth_type=env("WAQA_GENERIC_AUTH_TYPE", "bearer"),
            generic_auth_header=env("WAQA_GENERIC_AUTH_HEADER", "Authorization"),
            generic_auth_query_param=env("WAQA_GENERIC_AUTH_QUERY_PARAM", "token"),
            generic_auth_token=env("WAQA_GENERIC_AUTH_TOKEN", ""),
            generic_headers_json=env("WAQA_GENERIC_HEADERS", ""),
            generic_body_template=env("WAQA_GENERIC_BODY_TEMPLATE", ""),
            generic_msg_id_path=env("WAQA_GENERIC_MSG_ID_PATH", ""),
            generic_inbound_text_path=env("WAQA_GENERIC_INBOUND_TEXT_PATH", ""),
            generic_inbound_from_path=env("WAQA_GENERIC_INBOUND_FROM_PATH", ""),
            generic_inbound_fromme_path=env("WAQA_GENERIC_INBOUND_FROMME_PATH", ""),
            inbox_path=env("WAQA_INBOX_PATH", "whatsapp_qa_inbox.jsonl"),
        )
