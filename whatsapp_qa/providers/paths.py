"""Extrator de caminho pontilhado (dotted-path) para navegar JSON de webhooks.

Os webhooks de cada gateway de WhatsApp entregam o texto recebido em posicoes
diferentes. Em vez de codigo especifico por provedor, o provider generico usa um
caminho configuravel para localizar o valor.

Sintaxe suportada:
    chave                acessa a chave de um objeto           -> obj["chave"]
    a.b.c                aninhamento                            -> obj["a"]["b"]["c"]
    lista[0]             indice em lista                        -> obj["lista"][0]
    lista[-1]            indice negativo                        -> ultimo item
    lista[]              wildcard: primeiro item da lista em    -> procura em cada
                         que o RESTANTE do caminho resolve         item ate achar

Exemplos:
    get_path(payload, "messages[0].text.body")
    get_path(payload, "data[].message.conversation")   # Evolution/Baileys
    get_path(payload, "entry[].changes[].value.messages[].text.body")  # Meta
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"\[\s*(-?\d+)?\s*\]|[^.\[\]]+")


def _tokenize(path: str) -> list[str]:
    """Quebra o caminho em tokens: chaves e '[n]'/'[]'."""
    tokens: list[str] = []
    for m in _TOKEN_RE.finditer(path):
        piece = m.group(0)
        if piece.startswith("["):
            idx = m.group(1)
            tokens.append(f"[{idx}]" if idx is not None else "[]")
        else:
            key = piece.strip()
            if key:
                tokens.append(key)
    return tokens


def _resolve(obj: Any, tokens: list[str]) -> Any:
    if not tokens:
        return obj
    tok, rest = tokens[0], tokens[1:]

    if tok == "[]":  # wildcard: primeiro item cujo restante resolve
        if isinstance(obj, list):
            for item in obj:
                got = _resolve(item, rest)
                if got is not None:
                    return got
        return None

    if tok.startswith("[") and tok.endswith("]"):  # indice
        try:
            i = int(tok[1:-1])
        except ValueError:
            return None
        if isinstance(obj, list) and -len(obj) <= i < len(obj):
            return _resolve(obj[i], rest)
        return None

    # chave de objeto
    if isinstance(obj, dict) and tok in obj:
        return _resolve(obj[tok], rest)
    return None


def get_path(obj: Any, path: str, default: Any = None) -> Any:
    """Retorna o PRIMEIRO valor no caminho, ou `default` se nao existir."""
    if not path:
        return default
    got = _resolve(obj, _tokenize(path))
    return default if got is None else got


def _resolve_all(obj: Any, tokens: list[str]) -> list:
    """Como _resolve, mas o wildcard [] acumula TODOS os itens que resolvem."""
    if not tokens:
        return [obj] if obj is not None else []
    tok, rest = tokens[0], tokens[1:]

    if tok == "[]":
        out: list = []
        if isinstance(obj, list):
            for item in obj:
                out.extend(_resolve_all(item, rest))
        return out

    if tok.startswith("[") and tok.endswith("]"):
        try:
            i = int(tok[1:-1])
        except ValueError:
            return []
        if isinstance(obj, list) and -len(obj) <= i < len(obj):
            return _resolve_all(obj[i], rest)
        return []

    if isinstance(obj, dict) and tok in obj:
        return _resolve_all(obj[tok], rest)
    return []


def get_path_all(obj: Any, path: str) -> list:
    """Retorna TODOS os valores que casam o caminho (wildcard [] expande a lista).

    Para caminhos sem wildcard, devolve `[valor]` ou `[]`. Usado para coletar
    varias mensagens entregues num unico POST de webhook (Meta agrupa em
    messages[], Zenvia em contents[], etc.), sem descartar as demais.
    """
    if not path:
        return []
    return _resolve_all(obj, _tokenize(path))
