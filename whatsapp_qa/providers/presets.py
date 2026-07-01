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
# 'generic_'). Campos ausentes usam o default do Config.
PRESETS: dict[str, dict] = {}


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
    for field, value in PRESETS[key].items():
        attr = f"generic_{field}"
        if not hasattr(config, attr):
            continue
        current = getattr(config, attr)
        # Preenche apenas se ainda estiver no default (nao foi definido por env).
        if current == getattr(defaults, attr, ""):
            setattr(config, attr, value)
