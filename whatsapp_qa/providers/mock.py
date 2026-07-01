"""Provider mock: simula um bot de WhatsApp em memoria.

Serve para validar o harness ponta a ponta (enviar -> aguardar -> avaliar ->
relatorio) sem WhatsApp real, sem credenciais e sem custo. O 'bot' embutido e
um respondedor simples baseado em regras; ajuste BOT_RULES para imitar o seu
assistente real durante o desenvolvimento.
"""

from __future__ import annotations

import time

from ..config import Config
from .base import InboundMessage, WhatsAppProvider

# Regras do bot simulado: (palavras-gatilho na mensagem recebida, resposta).
# A primeira regra cujos gatilhos aparecem na mensagem vence.
BOT_RULES: list[tuple[list[str], str]] = [
    (["oi", "ola", "bom dia", "boa tarde"], "Ola! Sou o assistente virtual. Como posso ajudar?"),
    (["abrir", "chamado", "ticket"], "Claro! Para abrir um chamado, me diga o assunto e a categoria."),
    (["horario", "funcionamento", "atendimento"], "Nosso atendimento e de segunda a sexta, das 8h as 18h."),
    (["status", "andamento", "protocolo"], "Para consultar o status, informe o numero do protocolo."),
    (["senha", "resetar", "redefinir"], "Para redefinir a senha, acesse o portal e clique em 'Esqueci minha senha'."),
    (["humano", "atendente", "pessoa"], "Vou te transferir para um atendente humano. Aguarde um momento."),
]

DEFAULT_REPLY = "Desculpe, nao entendi. Pode reformular?"


def _default_bot(text: str) -> str:
    lowered = text.lower()
    for triggers, reply in BOT_RULES:
        if any(t in lowered for t in triggers):
            return reply
    return DEFAULT_REPLY


class MockProvider(WhatsAppProvider):
    """Loopback em memoria com um bot de regras."""

    def __init__(self, config: Config, bot=_default_bot) -> None:
        self.config = config
        self._bot = bot
        self._inbox: list[InboundMessage] = []
        self._counter = 0

    def send_text(self, to: str, body: str) -> str:
        self._counter += 1
        msg_id = f"mock-{self._counter}"
        # O 'bot' responde imediatamente; gravamos na inbox como se tivesse chegado.
        reply = self._bot(body)
        # Pequeno avanco de relogio para garantir timestamp > since do envio.
        self._inbox.append(
            InboundMessage(text=reply, timestamp=time.time(), raw={"in_reply_to": msg_id})
        )
        return msg_id

    def fetch_since(self, since: float) -> list[InboundMessage]:
        return [m for m in self._inbox if m.timestamp > since]
