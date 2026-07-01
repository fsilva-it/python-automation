"""Camada de transporte (providers) do harness de WhatsApp.

Cada provider implementa o contrato em base.WhatsAppProvider. A escolha e feita
em tempo de execucao por config.Config.provider.
"""

from __future__ import annotations

from ..config import Config
from .base import InboundMessage, WhatsAppProvider


def build_provider(config: Config) -> WhatsAppProvider:
    """Instancia o provider conforme a configuracao."""
    name = (config.provider or "mock").lower()
    if name == "mock":
        from .mock import MockProvider

        return MockProvider(config)
    if name == "cloud":
        from .cloud_api import CloudApiProvider

        return CloudApiProvider(config)
    if name == "twilio":
        from .twilio_api import TwilioProvider

        return TwilioProvider(config)
    if name in ("generic", "provedor", "gateway"):
        from .generic import GenericProvider

        return GenericProvider(config)
    raise ValueError(
        f"Provider desconhecido: {name!r}. Use 'mock', 'cloud', 'twilio' ou 'generic'."
    )


__all__ = ["build_provider", "WhatsAppProvider", "InboundMessage"]
