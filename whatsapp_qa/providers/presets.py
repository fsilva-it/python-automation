"""Presets de configuracao para gateways de WhatsApp conhecidos.

Um preset preenche os campos generic_* com defaults sensatos de um provedor
especifico, para que so falte informar URL/token. Variaveis de ambiente sempre
tem prioridade sobre o preset (o preset so preenche o que ficou no default).

Os valores de cada preset refletem o formato publico de API/webhook de cada
gateway. Confirme na reuniao com o provedor e ajuste por env var se divergir.

Placeholders nos templates:
    {{to}}   numero de destino (E.164)
    {{body}} texto da mensagem

Este dicionario e populado a partir da pesquisa de formatos (ver
docs/REUNIAO-PROVEDOR.md). Provedores nao listados podem ser configurados
inteiramente por variaveis de ambiente WAQA_GENERIC_*.
"""

from __future__ import annotations

# Cada preset e um dict com um subconjunto dos campos generic_* (sem o prefixo
# 'generic_'). Campos ausentes usam o default do Config. Chaves extras
# ('provider', 'official', 'send_url_template', 'note') sao apenas documentacao e
# ignoradas por apply_preset (nao existe atributo generic_<chave> correspondente).
#
# Formatos confirmados por pesquisa cruzada da documentacao de cada gateway
# (ver docs/REUNIAO-PROVEDOR.md). O operador SEMPRE informa a URL real de envio
# em WAQA_GENERIC_SEND_URL e o token em WAQA_GENERIC_AUTH_TOKEN.
PRESETS: dict[str, dict] = {
    # --- Gateways baseados em WhatsApp Web (nao oficiais Meta) - mais provaveis ---
    "evolution": {
        "provider": "Evolution API (v2, Baileys)",
        "official": False,
        "send_url_template": "https://{server-url}/message/sendText/{instance}",
        "method": "POST",
        "content_type": "json",
        "auth_type": "header",
        "auth_header": "apikey",
        "body_template": '{"number": "{{to}}", "text": "{{body}}"}',
        "msg_id_path": "key.id",
        "inbound_text_path": "data.message.conversation",
        "inbound_from_path": "data.key.remoteJid",
        "inbound_fromme_path": "data.key.fromMe",
        "note": "Use a apikey da INSTANCIA. Texto com link/citacao pode vir em "
                "data.message.extendedTextMessage.text (validar com payload real).",
    },
    "wppconnect": {
        "provider": "WPPConnect Server (WA-JS)",
        "official": False,
        "send_url_template": "http://{host}:{port}/api/{session}/send-message",
        "method": "POST",
        "content_type": "json",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "body_template": '{"phone": "{{to}}", "message": "{{body}}"}',
        "msg_id_path": "response.id",
        "inbound_text_path": "body",
        "inbound_from_path": "from",
        "inbound_fromme_path": "fromMe",
        "note": "Token vem de /api/{session}/{SECRET}/generate-token (campo 'full'). "
                "msg_id_path pode variar por versao (validar).",
    },
    "zapi": {
        "provider": "Z-API (z-api.io)",
        "official": False,
        # instanceId e token da instancia ja embutidos na URL:
        "send_url_template": "https://api.z-api.io/instances/{instanceId}/token/{token}/send-text",
        "method": "POST",
        "content_type": "json",
        # Token de CONTA (Client-Token) vai no header; o token de INSTANCIA fica na URL.
        "auth_type": "header",
        "auth_header": "Client-Token",
        "body_template": '{"phone": "{{to}}", "message": "{{body}}"}',
        "msg_id_path": "messageId",
        "inbound_text_path": "text.message",
        "inbound_from_path": "phone",
        "inbound_fromme_path": "fromMe",
        "note": "WAQA_GENERIC_AUTH_TOKEN = Client-Token da CONTA (dashboard). O token "
                "da INSTANCIA vai embutido na WAQA_GENERIC_SEND_URL.",
    },
    # --- BSPs oficiais Meta (cobertura extra; cloud/twilio tem provider dedicado) ---
    "cloud": {
        "provider": "WhatsApp Cloud API (Meta)",
        "official": True,
        "send_url_template": "https://graph.facebook.com/{version}/{phone-number-id}/messages",
        "method": "POST",
        "content_type": "json",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "body_template": '{"messaging_product": "whatsapp", "recipient_type": "individual", '
                         '"to": "{{to}}", "type": "text", "text": {"preview_url": false, "body": "{{body}}"}}',
        "msg_id_path": "messages[0].id",
        "inbound_text_path": "entry[].changes[].value.messages[].text.body",
        "inbound_from_path": "entry[].changes[].value.messages[].from",
        "inbound_fromme_path": "",
        "note": "Prefira o provider dedicado 'cloud'. Sem fromMe: enviadas chegam em statuses[] (nao viram eco).",
    },
    "360dialog": {
        "provider": "360dialog (BSP oficial, waba-v2)",
        "official": True,
        "send_url_template": "https://waba-v2.360dialog.io/messages",
        "method": "POST",
        "content_type": "json",
        "auth_type": "header",
        "auth_header": "D360-API-KEY",
        "body_template": '{"messaging_product": "whatsapp", "recipient_type": "individual", '
                         '"to": "{{to}}", "type": "text", "text": {"body": "{{body}}"}}',
        "msg_id_path": "messages[0].id",
        "inbound_text_path": "entry[].changes[].value.messages[].text.body",
        "inbound_from_path": "entry[].changes[].value.messages[].from",
        "inbound_fromme_path": "",
    },
    "twilio": {
        "provider": "Twilio API for WhatsApp",
        "official": True,
        "send_url_template": "https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json",
        "method": "POST",
        "content_type": "form",
        "auth_type": "basic",  # WAQA_GENERIC_AUTH_TOKEN = "AccountSid:AuthToken"
        "auth_header": "Authorization",
        # ATENCAO: substitua {FROM_NUMBER} pelo seu numero remetente (sem '+').
        "body_template": '{"To": "whatsapp:+{{to}}", "From": "whatsapp:+{FROM_NUMBER}", "Body": "{{body}}"}',
        "msg_id_path": "sid",
        "inbound_text_path": "Body",
        "inbound_from_path": "From",
        "inbound_fromme_path": "",
        "note": "Prefira o provider dedicado 'twilio'. Substitua {FROM_NUMBER} no body_template.",
    },
    "gupshup": {
        "provider": "Gupshup (BSP oficial)",
        "official": True,
        "send_url_template": "https://api.gupshup.io/wa/api/v1/msg",
        "method": "POST",
        "content_type": "form",
        "auth_type": "header",
        "auth_header": "apikey",
        # ATENCAO: substitua {SOURCE_PHONE} e {APP_NAME}. 'message' e uma string JSON aninhada.
        "body_template": '{"channel": "whatsapp", "source": "{SOURCE_PHONE}", "destination": "{{to}}", '
                         '"src.name": "{APP_NAME}", "message": "{\\"type\\":\\"text\\",\\"text\\":\\"{{body}}\\"}"}',
        "msg_id_path": "messageId",
        "inbound_text_path": "payload.payload.text",
        "inbound_from_path": "payload.sender.phone",
        "inbound_fromme_path": "",
        "note": "Substitua {SOURCE_PHONE} e {APP_NAME} no body_template antes de usar. "
                "LIMITACAO: o campo 'message' e um JSON dentro de string; um texto com "
                "aspas duplas nao e re-escapado para o nivel interno - evite aspas no "
                "checklist ou use uma integracao dedicada para este gateway.",
    },
    "zenvia": {
        "provider": "Zenvia (BSP oficial)",
        "official": True,
        "send_url_template": "https://api.zenvia.com/v1/channels/whatsapp/messages",
        "method": "POST",
        "content_type": "json",
        "auth_type": "header",
        "auth_header": "X-API-TOKEN",
        # ATENCAO: substitua {FROM_IDENTIFIER} pelo seu identificador de origem.
        "body_template": '{"from": "{FROM_IDENTIFIER}", "to": "{{to}}", '
                         '"contents": [{"type": "text", "text": "{{body}}"}]}',
        "msg_id_path": "id",
        "inbound_text_path": "message.contents[].text",
        "inbound_from_path": "message.from",
        "inbound_fromme_path": "",
        "note": "Substitua {FROM_IDENTIFIER} no body_template antes de usar.",
    },
}


def preset_names() -> list[str]:
    return sorted(PRESETS)


def apply_preset(config) -> None:
    """Aplica o preset selecionado ao config, sem sobrescrever env vars.

    So preenche campos generic_* que ainda estao no valor padrao (indicando que
    o usuario nao os definiu por ambiente).
    """
    key = (config.generic_preset or "").strip().lower()
    if not key:
        return
    if key not in PRESETS:
        raise ValueError(
            f"Preset desconhecido: {key!r}. Disponiveis: {preset_names() or '(nenhum)'}."
        )

    from ..config import Config

    defaults = Config()
    env_provided = getattr(config, "_env_provided", set()) or set()
    for field, value in PRESETS[key].items():
        attr = f"generic_{field}"
        if not hasattr(config, attr):
            continue  # chaves de documentacao (provider, note, ...) sao ignoradas
        # A env sempre vence o preset: nao preenche se o campo foi definido por
        # ambiente OU se ja difere do default (definido explicitamente).
        if attr in env_provided:
            continue
        if getattr(config, attr) != getattr(defaults, attr, ""):
            continue
        setattr(config, attr, value)
