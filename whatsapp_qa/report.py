"""Renderizacao do resultado: console, JSON e Markdown."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .runner import CaseOutcome


def _summary(outcomes: list[CaseOutcome]) -> tuple[int, int]:
    passed = sum(1 for o in outcomes if o.passed)
    return passed, len(outcomes)


def to_console(outcomes: list[CaseOutcome]) -> str:
    lines: list[str] = []
    for o in outcomes:
        mark = "PASS" if o.passed else "FALHOU"
        lines.append(f"[{mark}] {o.case.id}  ({o.grade.method}, {o.elapsed:.1f}s)")
        lines.append(f"    enviado : {o.case.send}")
        resp = o.response.replace("\n", " ") or "(sem resposta)"
        lines.append(f"    resposta: {resp[:280]}")
        lines.append(f"    motivo  : {o.grade.rationale}")
    passed, total = _summary(outcomes)
    lines.append("")
    lines.append(f"Resultado: {passed}/{total} aprovados "
                 f"({(passed / total * 100) if total else 0:.0f}%).")
    return "\n".join(lines)


def to_json(outcomes: list[CaseOutcome], generated_at: str | None = None) -> str:
    passed, total = _summary(outcomes)
    payload = {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "summary": {
            "passed": passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0,
        },
        "cases": [
            {
                "id": o.case.id,
                "category": o.case.category,
                "sent": o.case.send,
                "expected": o.case.describe_expectation(),
                "response": o.response,
                "passed": o.passed,
                "method": o.grade.method,
                "rationale": o.grade.rationale,
                "elapsed_seconds": round(o.elapsed, 3),
                "error": o.error,
            }
            for o in outcomes
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def to_markdown(outcomes: list[CaseOutcome], generated_at: str | None = None) -> str:
    passed, total = _summary(outcomes)
    ts = generated_at or datetime.now(timezone.utc).isoformat()
    lines = [
        "# Relatorio de teste - assistente de WhatsApp",
        "",
        f"Gerado em: {ts}",
        "",
        f"Resultado: **{passed}/{total} aprovados** "
        f"({(passed / total * 100) if total else 0:.0f}%).",
        "",
        "| Caso | Categoria | Resultado | Metodo | Motivo |",
        "| --- | --- | --- | --- | --- |",
    ]
    for o in outcomes:
        status = "Aprovado" if o.passed else "Reprovado"
        motivo = o.grade.rationale.replace("|", "\\|")
        lines.append(f"| {o.case.id} | {o.case.category or '-'} | {status} | {o.grade.method} | {motivo} |")
    return "\n".join(lines)


def render(outcomes: list[CaseOutcome], fmt: str) -> str:
    fmt = fmt.lower()
    if fmt == "json":
        return to_json(outcomes)
    if fmt in ("md", "markdown"):
        return to_markdown(outcomes)
    return to_console(outcomes)
