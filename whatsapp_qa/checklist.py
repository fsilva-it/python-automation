"""Carga e validacao do checklist de testes.

O checklist e uma lista de casos. Cada caso tem uma mensagem a enviar e o
criterio esperado para a resposta do bot. Formatos aceitos: YAML (se pyyaml
estiver instalado) ou JSON.

Exemplo (YAML):

    - id: saudacao
      send: "Oi"
      expect_keywords: ["ola", "posso ajudar"]
    - id: abrir_chamado
      send: "Quero abrir um chamado"
      expect: "O bot deve explicar como abrir um chamado ou pedir o assunto."
      grader: ai
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TestCase:
    """Um caso de teste: a mensagem enviada e o criterio de aprovacao."""

    id: str
    send: str
    # Criterio em linguagem natural (usado pelo avaliador de IA).
    expect: str = ""
    # Palavras/expressoes que devem aparecer na resposta (avaliador keyword).
    expect_keywords: list[str] = field(default_factory=list)
    # Resposta exata esperada (avaliador exact).
    expect_exact: str = ""
    # Sobrescreve o avaliador global so para este caso.
    grader: str = ""
    # Categoria livre para agrupar no relatorio.
    category: str = ""

    def describe_expectation(self) -> str:
        """Texto legivel do que se espera, para relatorio e prompt de IA."""
        if self.expect:
            return self.expect
        if self.expect_keywords:
            return "Deve conter: " + ", ".join(repr(k) for k in self.expect_keywords)
        if self.expect_exact:
            return f"Deve ser exatamente: {self.expect_exact!r}"
        return "(sem criterio definido)"


class ChecklistError(ValueError):
    """Erro de formato/validacao do arquivo de checklist."""


def _coerce_case(raw: dict[str, Any], index: int) -> TestCase:
    if not isinstance(raw, dict):
        raise ChecklistError(f"Caso #{index} deve ser um objeto/dicionario, veio {type(raw).__name__}.")

    send = raw.get("send")
    if not isinstance(send, str) or not send.strip():
        raise ChecklistError(f"Caso #{index} ('{raw.get('id', '?')}') precisa de um campo 'send' nao vazio.")

    keywords = raw.get("expect_keywords", []) or []
    if isinstance(keywords, str):
        keywords = [keywords]
    if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
        raise ChecklistError(f"Caso #{index}: 'expect_keywords' deve ser lista de strings.")

    case = TestCase(
        id=str(raw.get("id") or f"caso_{index}"),
        send=send,
        expect=str(raw.get("expect", "") or ""),
        expect_keywords=list(keywords),
        expect_exact=str(raw.get("expect_exact", "") or ""),
        grader=str(raw.get("grader", "") or ""),
        category=str(raw.get("category", "") or ""),
    )

    if not (case.expect or case.expect_keywords or case.expect_exact):
        raise ChecklistError(
            f"Caso '{case.id}' nao tem criterio: defina ao menos um de "
            "'expect', 'expect_keywords' ou 'expect_exact'."
        )
    return case


def _parse_text(text: str, suffix: str) -> Any:
    suffix = suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise ChecklistError(
                "Arquivo YAML requer o pacote pyyaml. Instale com 'pip install pyyaml' "
                "ou converta o checklist para JSON."
            ) from exc
        return yaml.safe_load(text)
    return json.loads(text)


def load_checklist(path: str | Path) -> list[TestCase]:
    """Carrega e valida o checklist do disco, retornando casos prontos para rodar."""
    p = Path(path)
    if not p.exists():
        raise ChecklistError(f"Checklist nao encontrado: {p}")

    data = _parse_text(p.read_text(encoding="utf-8"), p.suffix)

    # Aceita tanto uma lista no topo quanto {"cases": [...]}.
    if isinstance(data, dict) and "cases" in data:
        data = data["cases"]
    if not isinstance(data, list):
        raise ChecklistError("O checklist deve ser uma lista de casos (ou {'cases': [...]}).")
    if not data:
        raise ChecklistError("O checklist esta vazio.")

    cases = [_coerce_case(raw, i) for i, raw in enumerate(data)]

    ids = [c.id for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ChecklistError(f"IDs de caso duplicados: {sorted(dupes)}")

    return cases
