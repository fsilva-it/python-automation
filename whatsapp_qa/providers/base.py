"""Contrato comum a todos os providers de WhatsApp."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class InboundMessage:
    """Uma mensagem recebida do bot que esta sendo testado."""

    text: str
    timestamp: float  # epoch em segundos (quando o harness viu a mensagem)
    raw: dict | None = None  # payload bruto do provider, para depuracao


class WhatsAppProvider(ABC):
    """Transporte: envia mensagens e coleta respostas do bot sob teste.

    O modelo de teste e: o harness atua como 'cliente', envia para o numero do
    bot e aguarda as respostas que o bot devolve ao numero do harness.
    """

    @abstractmethod
    def send_text(self, to: str, body: str) -> str:
        """Envia uma mensagem de texto. Retorna o id da mensagem enviada."""

    @abstractmethod
    def fetch_since(self, since: float) -> list[InboundMessage]:
        """Retorna mensagens recebidas com timestamp > since."""

    def wait_for_reply(
        self,
        since: float,
        timeout: float,
        poll_interval: float = 1.0,
        quiet_period: float = 2.0,
    ) -> list[InboundMessage]:
        """Aguarda a(s) resposta(s) do bot apos um envio.

        Coleta tudo que chegar depois de `since`. Quando a primeira mensagem
        chega, espera um pequeno `quiet_period` para capturar respostas em
        varias bolhas antes de devolver. Retorna lista vazia em timeout.
        """
        deadline = time.monotonic() + timeout
        collected: list[InboundMessage] = []
        last_seen_ts = since

        while time.monotonic() < deadline:
            batch = self.fetch_since(last_seen_ts)
            if batch:
                collected.extend(batch)
                last_seen_ts = max(m.timestamp for m in batch)
                # Janela de silencio para agrupar mensagens fragmentadas.
                quiet_deadline = time.monotonic() + quiet_period
                while time.monotonic() < quiet_deadline:
                    time.sleep(poll_interval)
                    more = self.fetch_since(last_seen_ts)
                    if more:
                        collected.extend(more)
                        last_seen_ts = max(m.timestamp for m in more)
                        quiet_deadline = time.monotonic() + quiet_period
                break
            time.sleep(poll_interval)

        return collected

    def close(self) -> None:
        """Libera recursos (sobrescreva se necessario)."""
