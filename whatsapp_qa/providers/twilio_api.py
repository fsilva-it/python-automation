"""Provider para o Twilio API for WhatsApp.

Envio: REST API da Twilio (Messages).
Recebimento: configure o webhook de mensagem recebida da Twilio apontando para
webhook.py, que grava na inbox lida aqui.

Requisitos de ambiente:
    WAQA_TWILIO_ACCOUNT_SID
    WAQA_TWILIO_AUTH_TOKEN
    WAQA_TWILIO_FROM       - ex: "whatsapp:+14155238886"
    WAQA_TARGET_NUMBER     - numero do bot sob teste (E.164, so digitos)
"""

from __future__ import annotations

from ..config import Config
from .base import InboundMessage, WhatsAppProvider
from .inbox import read_since


def _wa(number: str) -> str:
    """Garante o prefixo 'whatsapp:' que a Twilio exige."""
    number = number.strip()
    if number.startswith("whatsapp:"):
        return number
    if not number.startswith("+"):
        number = "+" + number
    return f"whatsapp:{number}"


class TwilioProvider(WhatsAppProvider):
    def __init__(self, config: Config) -> None:
        self.config = config
        if not config.twilio_account_sid or not config.twilio_auth_token or not config.twilio_from:
            raise ValueError(
                "Twilio requer WAQA_TWILIO_ACCOUNT_SID, WAQA_TWILIO_AUTH_TOKEN e WAQA_TWILIO_FROM."
            )
        try:
            import requests  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Provider 'twilio' requer o pacote 'requests' (pip install requests).") from exc
        self._requests = requests
        self._url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{config.twilio_account_sid}/Messages.json"
        )

    def send_text(self, to: str, body: str) -> str:
        resp = self._requests.post(
            self._url,
            auth=(self.config.twilio_account_sid, self.config.twilio_auth_token),
            data={"From": _wa(self.config.twilio_from), "To": _wa(to), "Body": body},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Twilio erro {resp.status_code}: {resp.text}")
        return resp.json().get("sid", "sent")

    def fetch_since(self, since: float) -> list[InboundMessage]:
        return read_since(self.config.inbox_path, since)
