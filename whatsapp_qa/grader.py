"""Avaliacao da resposta do bot contra o criterio do caso de teste.

Estrategias:
    keyword - aprova se todas (ou as configuradas) palavras-chave aparecem
    exact   - aprova se a resposta normalizada bate exatamente
    ai      - usa Claude para julgar se a resposta atende ao criterio
    hybrid  - tenta keyword/exact primeiro; em caso ambiguo, recorre a IA
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .checklist import TestCase
from .config import Config


@dataclass
class GradeResult:
    passed: bool
    method: str  # qual estrategia decidiu (keyword/exact/ai/none)
    rationale: str  # explicacao curta do porque passou/falhou


def _normalize(text: str) -> str:
    """Minusculo, sem acento, espacos colapsados - para comparacao robusta."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def grade_keyword(case: TestCase, response: str) -> GradeResult:
    norm = _normalize(response)
    missing = [k for k in case.expect_keywords if _normalize(k) not in norm]
    if missing:
        return GradeResult(False, "keyword", f"Faltaram palavras-chave: {missing}")
    return GradeResult(True, "keyword", "Todas as palavras-chave presentes.")


def grade_exact(case: TestCase, response: str) -> GradeResult:
    if _normalize(case.expect_exact) == _normalize(response):
        return GradeResult(True, "exact", "Resposta identica ao esperado.")
    return GradeResult(False, "exact", "Resposta difere do texto exato esperado.")


def grade_ai(case: TestCase, response: str, config: Config) -> GradeResult:
    if not config.anthropic_api_key:
        return GradeResult(
            False, "ai",
            "Avaliacao por IA indisponivel: defina ANTHROPIC_API_KEY (ou WAQA_ANTHROPIC_API_KEY).",
        )
    try:
        import anthropic  # type: ignore
    except ImportError:
        return GradeResult(False, "ai", "Pacote 'anthropic' nao instalado (pip install anthropic).")

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    criterio = case.describe_expectation()
    prompt = (
        "Voce e um avaliador de QA de um assistente de WhatsApp. Decida se a RESPOSTA "
        "do bot atende ao CRITERIO esperado. Seja rigoroso, mas aceite variacoes de "
        "forma desde que o conteudo atenda.\n\n"
        f"MENSAGEM ENVIADA AO BOT:\n{case.send}\n\n"
        f"CRITERIO ESPERADO:\n{criterio}\n\n"
        f"RESPOSTA DO BOT:\n{response}\n\n"
        "Responda APENAS com uma linha no formato: VEREDITO|justificativa\n"
        "onde VEREDITO e PASS ou FAIL. Justificativa em uma frase curta."
    )
    try:
        msg = client.messages.create(
            model=config.anthropic_model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text").strip()
    except Exception as exc:  # pragma: no cover - rede/credencial
        return GradeResult(False, "ai", f"Falha ao consultar a IA: {exc}")

    verdict, _, rationale = text.partition("|")
    passed = verdict.strip().upper().startswith("PASS")
    return GradeResult(passed, "ai", rationale.strip() or text)


def grade(case: TestCase, response: str, config: Config) -> GradeResult:
    """Aplica a estrategia do caso (ou a global) sobre a resposta."""
    if not response.strip():
        return GradeResult(False, "none", "Bot nao respondeu (timeout ou resposta vazia).")

    strategy = (case.grader or config.grader or "hybrid").lower()

    if strategy == "exact":
        return grade_exact(case, response)
    if strategy == "keyword":
        return grade_keyword(case, response)
    if strategy == "ai":
        return grade_ai(case, response, config)

    # hybrid: usa o criterio mais especifico disponivel; IA como reforco/fallback.
    if case.expect_exact:
        res = grade_exact(case, response)
        if res.passed:
            return res
    if case.expect_keywords:
        res = grade_keyword(case, response)
        if res.passed:
            return res
        # Keyword falhou mas ha criterio em linguagem natural -> tenta IA.
        if case.expect and config.anthropic_api_key:
            return grade_ai(case, response, config)
        return res
    if case.expect:
        return grade_ai(case, response, config)

    return GradeResult(False, "none", "Caso sem criterio avaliavel.")
