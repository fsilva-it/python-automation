"""Interface de linha de comando do harness.

Exemplos:
    # Bateria de demonstracao (bot simulado, sem WhatsApp real):
    python -m whatsapp_qa run --checklist checklists/exemplo.yaml

    # Contra um numero real via Cloud API, relatorio em Markdown:
    WAQA_PROVIDER=cloud WAQA_TARGET_NUMBER=5511999999999 \
    python -m whatsapp_qa run --checklist checklists/meu.yaml --format md --out relatorio.md
"""

from __future__ import annotations

import argparse
import sys

from .checklist import ChecklistError, load_checklist
from .config import Config
from .providers import build_provider
from .report import render
from .runner import CaseOutcome, run_checklist


def _live_progress(outcome: CaseOutcome) -> None:
    mark = "PASS" if outcome.passed else "FALHOU"
    print(f"  [{mark}] {outcome.case.id} ({outcome.grade.method})", file=sys.stderr)


def cmd_run(args: argparse.Namespace) -> int:
    config = Config.from_env()
    if args.provider:
        config.provider = args.provider
    if args.target:
        config.target_number = args.target

    if config.provider != "mock" and not config.target_number:
        print("Erro: defina WAQA_TARGET_NUMBER (ou --target) para providers reais.", file=sys.stderr)
        return 2

    try:
        cases = load_checklist(args.checklist)
    except ChecklistError as exc:
        print(f"Erro no checklist: {exc}", file=sys.stderr)
        return 2

    print(f"Provider: {config.provider} | casos: {len(cases)} | avaliador: {config.grader}",
          file=sys.stderr)

    provider = build_provider(config)
    try:
        outcomes = run_checklist(provider, cases, config, on_result=_live_progress)
    finally:
        provider.close()

    output = render(outcomes, args.format)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(output + "\n")
        print(f"Relatorio salvo em {args.out}", file=sys.stderr)
    else:
        print(output)

    passed = sum(1 for o in outcomes if o.passed)
    # Codigo de saida != 0 se algum caso reprovou (util para CI).
    return 0 if passed == len(outcomes) else 1


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        cases = load_checklist(args.checklist)
    except ChecklistError as exc:
        print(f"Invalido: {exc}", file=sys.stderr)
        return 2
    print(f"OK: {len(cases)} casos validos em {args.checklist}.")
    for c in cases:
        print(f"  - {c.id}: {c.describe_expectation()[:80]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="whatsapp_qa", description="Harness de teste de WhatsApp por checklist.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Executa o checklist contra o WhatsApp.")
    run.add_argument("--checklist", required=True, help="Caminho do arquivo YAML/JSON.")
    run.add_argument("--provider", choices=["mock", "cloud", "twilio"], help="Sobrescreve WAQA_PROVIDER.")
    run.add_argument("--target", help="Numero do bot sob teste (E.164). Sobrescreve WAQA_TARGET_NUMBER.")
    run.add_argument("--format", default="console", choices=["console", "json", "md", "markdown"])
    run.add_argument("--out", help="Salva o relatorio em arquivo em vez de stdout.")
    run.set_defaults(func=cmd_run)

    val = sub.add_parser("validate", help="Valida o formato do checklist sem enviar nada.")
    val.add_argument("--checklist", required=True)
    val.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
