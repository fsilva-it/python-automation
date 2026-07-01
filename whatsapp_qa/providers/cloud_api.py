"""Provider para a WhatsApp Cloud API oficial (Meta).

Envio: POST para a Graph API (graph.facebook.com).
Recebimento: as respostas do bot chegam ao seu webhook; rode webhook.py para
gravar na inbox que este provider le.

Requisitos de ambiente:
    WAQA_CLOUD_PHONE_NUMBER_ID  - id do numero remetente (o numero do harness)
    WAQA_CLOUD_ACCESS_TOKEN     - token de acesso permanente/temporario
    WAQA_TARGET_NUMBER          - numero do bot sob teste (E.164, so digitos)

Observacao de conformidade: fora da janela de 24h de atendimento, a Cloud API so
permite enviar 'templates' aprovados. Para um harness de QA, mantenha a janela
aberta (o bot deve ter interagido) ou use templates como mensagem de teste.
"""

from __future__ import annotations

from ..config import Config
from .base import InboundMessage, WhatsAppProvider, safe_error_snippet
from .inbox import read_since


class CloudApiProvider(WhatsAppProvider):
    def __init__(self, config: Config) -> None:
        self.config = config
        if not config.cloud_phone_number_id or not config.cloud_access_token:
            raise ValueError(
                "Cloud API requer WAQA_CLOUD_PHONE_NUMBER_ID e WAQA_CLOUD_ACCESS_TOKEN."
            )
        try:
            import requests  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Provider 'cloud' requer o pacote 'requests' (pip install requests).") from exc
        self._requests = requests
        self._base = (
            f"https://graph.facebook.com/{config.cloud_api_version}/"
            f"{config.cloud_phone_number_id}/messages"
        )

    def send_text(self, to: str, body: str) -> str:
        resp = self._requests.post(
            self._base,
            headers={
                "Authorization": f"Bearer {self.config.cloud_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"preview_url": False, "body": body},
            },
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Cloud API erro {resp.status_code}: {safe_error_snippet(resp.text)}")
        data = resp.json()
        try:
            return data["messages"][0]["id"]
        except (KeyError, IndexError):
            return "sent"

    def fetch_since(self, since: float) -> list[InboundMessage]:
        return read_since(self.config.inbox_path, since)
