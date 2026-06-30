"""Testes do nucleo do harness (sem rede, sem WhatsApp real).

Rode com: python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from whatsapp_qa.checklist import ChecklistError, TestCase, load_checklist
from whatsapp_qa.config import Config
from whatsapp_qa.grader import grade
from whatsapp_qa.providers.mock import MockProvider
from whatsapp_qa.runner import run_checklist


class GraderTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(grader="keyword", anthropic_api_key="")

    def test_keyword_pass_ignores_accent_and_case(self):
        case = TestCase(id="t", send="oi", expect_keywords=["Olá", "AJUDAR"])
        res = grade(case, "ola, como posso ajudar voce?", self.config)
        self.assertTrue(res.passed)
        self.assertEqual(res.method, "keyword")

    def test_keyword_fail_lists_missing(self):
        case = TestCase(id="t", send="oi", expect_keywords=["protocolo"])
        res = grade(case, "ola!", self.config)
        self.assertFalse(res.passed)
        self.assertIn("protocolo", res.rationale)

    def test_empty_response_fails(self):
        case = TestCase(id="t", send="oi", expect_keywords=["x"])
        res = grade(case, "   ", self.config)
        self.assertFalse(res.passed)
        self.assertEqual(res.method, "none")

    def test_exact_normalizes(self):
        cfg = Config(grader="exact")
        case = TestCase(id="t", send="oi", expect_exact="Ola Mundo")
        self.assertTrue(grade(case, "  ola   mundo ", cfg).passed)

    def test_ai_without_key_fails_gracefully(self):
        cfg = Config(grader="ai", anthropic_api_key="")
        case = TestCase(id="t", send="oi", expect="qualquer coisa")
        res = grade(case, "resposta", cfg)
        self.assertFalse(res.passed)
        self.assertIn("ANTHROPIC", res.rationale.upper())


class ChecklistTests(unittest.TestCase):
    def _write(self, content: str, suffix: str) -> str:
        f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_load_json_list(self):
        path = self._write(json.dumps([
            {"id": "a", "send": "oi", "expect_keywords": ["ola"]},
        ]), ".json")
        cases = load_checklist(path)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].id, "a")

    def test_missing_criterion_raises(self):
        path = self._write(json.dumps([{"id": "a", "send": "oi"}]), ".json")
        with self.assertRaises(ChecklistError):
            load_checklist(path)

    def test_duplicate_ids_raise(self):
        path = self._write(json.dumps([
            {"id": "a", "send": "oi", "expect_keywords": ["x"]},
            {"id": "a", "send": "tchau", "expect_keywords": ["y"]},
        ]), ".json")
        with self.assertRaises(ChecklistError):
            load_checklist(path)

    def test_empty_send_raises(self):
        path = self._write(json.dumps([{"id": "a", "send": "  ", "expect_keywords": ["x"]}]), ".json")
        with self.assertRaises(ChecklistError):
            load_checklist(path)


class EndToEndMockTests(unittest.TestCase):
    def test_full_run_against_mock_bot(self):
        cfg = Config(provider="mock", grader="keyword", target_number="123",
                     pause_between=0, reply_timeout=2)
        cases = [
            TestCase(id="ok", send="oi", expect_keywords=["ajudar"]),
            TestCase(id="falha", send="oi", expect_keywords=["protocolo"]),
        ]
        provider = MockProvider(cfg)
        outcomes = run_checklist(provider, cases, cfg)
        self.assertEqual(len(outcomes), 2)
        by_id = {o.case.id: o for o in outcomes}
        self.assertTrue(by_id["ok"].passed)
        self.assertFalse(by_id["falha"].passed)
        self.assertIn("ajudar", by_id["ok"].response.lower())


if __name__ == "__main__":
    unittest.main()
