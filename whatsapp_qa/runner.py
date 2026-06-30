"""Orquestra o ciclo de teste: enviar -> aguardar resposta -> avaliar."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .checklist import TestCase
from .config import Config
from .grader import GradeResult, grade
from .providers import WhatsAppProvider


@dataclass
class CaseOutcome:
    case: TestCase
    sent_ok: bool
    response: str
    grade: GradeResult
    elapsed: float
    error: str = ""

    @property
    def passed(self) -> bool:
        return self.sent_ok and self.grade.passed


def run_case(provider: WhatsAppProvider, case: TestCase, config: Config) -> CaseOutcome:
    start = time.time()
    try:
        since = time.time()
        provider.send_text(config.target_number, case.send)
    except Exception as exc:
        return CaseOutcome(
            case=case, sent_ok=False, response="",
            grade=GradeResult(False, "none", f"Falha no envio: {exc}"),
            elapsed=time.time() - start, error=str(exc),
        )

    replies = provider.wait_for_reply(since=since, timeout=config.reply_timeout)
    response = "\n".join(r.text for r in replies)
    result = grade(case, response, config)
    return CaseOutcome(
        case=case, sent_ok=True, response=response,
        grade=result, elapsed=time.time() - start,
    )


def run_checklist(
    provider: WhatsAppProvider,
    cases: list[TestCase],
    config: Config,
    on_result=None,
) -> list[CaseOutcome]:
    """Roda todos os casos sequencialmente (preserva ordem das respostas).

    on_result(outcome) e chamado apos cada caso, util para progresso ao vivo.
    """
    outcomes: list[CaseOutcome] = []
    for i, case in enumerate(cases):
        outcome = run_case(provider, case, config)
        outcomes.append(outcome)
        if on_result:
            on_result(outcome)
        # Pausa entre casos, exceto apos o ultimo.
        if i < len(cases) - 1 and config.pause_between > 0:
            time.sleep(config.pause_between)
    return outcomes
