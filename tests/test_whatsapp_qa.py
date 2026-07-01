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
from whatsapp_qa.providers.paths import get_path
from whatsapp_qa.runner import run_checklist


class PathTests(unittest.TestCase):
    def test_simple_key(self):
        self.assertEqual(get_path({"a": 1}, "a"), 1)

    def test_nested(self):
        self.assertEqual(get_path({"a": {"b": {"c": 9}}}, "a.b.c"), 9)

    def test_index(self):
        self.assertEqual(get_path({"m": [{"t": "x"}, {"t": "y"}]}, "m[1].t"), "y")

    def test_negative_index(self):
        self.assertEqual(get_path({"m": [1, 2, 3]}, "m[-1]"), 3)

    def test_wildcard_finds_first_match(self):
        payload = {"messages": [{"image": {}}, {"text": {"body": "ola"}}]}
        self.assertEqual(get_path(payload, "messages[].text.body"), "ola")

    def test_meta_cloud_shape(self):
        payload = {"entry": [{"changes": [{"value": {"messages": [{"text": {"body": "oi"}}]}}]}]}
        self.assertEqual(get_path(payload, "entry[].changes[].value.messages[].text.body"), "oi")

    def test_missing_returns_default(self):
        self.assertIsNone(get_path({"a": 1}, "a.b.c"))
        self.assertEqual(get_path({}, "x", default="fallback"), "fallback")

    def test_empty_path_returns_default(self):
        self.assertIsNone(get_path({"a": 1}, ""))


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


class GenericProviderTests(unittest.TestCase):
    def test_render_body_substitutes_and_escapes(self):
        from whatsapp_qa.providers.generic import render_body
        tpl = '{"number": "{{to}}", "text": "{{body}}"}'
        out = render_body(tpl, "5511999", 'Ola "mundo"\ncom quebra')
        self.assertEqual(out["number"], "5511999")
        self.assertEqual(out["text"], 'Ola "mundo"\ncom quebra')  # aspas/quebra preservadas

    def test_render_body_invalid_template_raises(self):
        from whatsapp_qa.providers.generic import render_body
        with self.assertRaises(ValueError):
            render_body('{"text": {{body}}}', "x", "y")  # placeholder sem aspas -> JSON invalido

    def test_missing_send_url_raises(self):
        from whatsapp_qa.providers.generic import GenericProvider
        cfg = Config(provider="generic", generic_body_template='{"t":"{{body}}"}')
        with self.assertRaises(ValueError):
            GenericProvider(cfg)

    def test_unknown_preset_raises(self):
        from whatsapp_qa.providers.presets import apply_preset
        cfg = Config(generic_preset="nao_existe")
        with self.assertRaises(ValueError):
            apply_preset(cfg)

    def test_preset_evolution_populates_fields(self):
        from whatsapp_qa.providers.presets import apply_preset
        cfg = Config(generic_preset="evolution")
        apply_preset(cfg)
        self.assertEqual(cfg.generic_auth_header, "apikey")
        self.assertEqual(cfg.generic_inbound_text_path, "data.message.conversation")
        self.assertIn("{{to}}", cfg.generic_body_template)

    def test_env_value_overrides_preset(self):
        from whatsapp_qa.providers.presets import apply_preset
        # Campo definido explicitamente (diferente do default) nao e sobrescrito.
        cfg = Config(generic_preset="evolution", generic_auth_header="X-Custom")
        apply_preset(cfg)
        self.assertEqual(cfg.generic_auth_header, "X-Custom")

    def test_preset_gupshup_template_renders_valid_json(self):
        from whatsapp_qa.providers.generic import render_body
        from whatsapp_qa.providers.presets import PRESETS
        out = render_body(PRESETS["gupshup"]["body_template"], "5511999", "ola")
        self.assertEqual(out["destination"], "5511999")
        # 'message' e uma string JSON aninhada contendo o texto:
        self.assertIn("ola", out["message"])

    def test_preset_doc_keys_ignored_by_apply(self):
        # Chaves de documentacao nao devem virar atributos nem quebrar apply.
        from whatsapp_qa.providers.presets import apply_preset
        cfg = Config(generic_preset="zapi")
        apply_preset(cfg)
        self.assertFalse(hasattr(cfg, "generic_provider"))
        self.assertFalse(hasattr(cfg, "generic_send_url_template"))
        # send_url NAO deve ser preenchida pelo preset (tem placeholders):
        self.assertEqual(cfg.generic_send_url, "")


class WebhookExtractionTests(unittest.TestCase):
    def test_generic_path_extraction(self):
        from whatsapp_qa.webhook import extract_texts
        cfg = Config(generic_inbound_text_path="data[].message.conversation")
        payload = {"data": [{"message": {"conversation": "resposta do bot"}}]}
        self.assertEqual(extract_texts(payload, cfg, "application/json"), ["resposta do bot"])

    def test_generic_skips_fromme_echo(self):
        from whatsapp_qa.webhook import extract_texts
        cfg = Config(
            generic_inbound_text_path="message.text",
            generic_inbound_fromme_path="key.fromMe",
        )
        echo = {"key": {"fromMe": True}, "message": {"text": "nossa propria msg"}}
        self.assertEqual(extract_texts(echo, cfg, "application/json"), [])
        reply = {"key": {"fromMe": False}, "message": {"text": "reply do bot"}}
        self.assertEqual(extract_texts(reply, cfg, "application/json"), ["reply do bot"])

    def test_cloud_fallback_without_generic_path(self):
        from whatsapp_qa.webhook import extract_texts
        cfg = Config()  # sem generic path -> usa deteccao Cloud API
        payload = {"entry": [{"changes": [{"value": {"messages": [
            {"type": "text", "text": {"body": "oi cloud"}}]}}]}]}
        self.assertEqual(extract_texts(payload, cfg, "application/json"), ["oi cloud"])


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
