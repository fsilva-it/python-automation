"""Provider generico configuravel para qualquer gateway/BSP de WhatsApp.

Cobre, apenas por configuracao (variaveis de ambiente WAQA_GENERIC_* ou um
preset), gateways como Evolution API, WPPConnect, Z-API, 360dialog, Gupshup,
Zenvia, etc. — sem escrever codigo novo por provedor.

Envio: HTTP configuravel (URL, metodo, auth, content-type, body template).
Recepcao: as respostas chegam ao webhook (webhook.py), que grava na inbox lida
aqui; o texto e localizado por um caminho pontilhado configuravel.
"""

from __future__ import annotations

import json

from ..config import Config
from .base import InboundMessage, WhatsAppProvider
from .inbox import read_since
from .paths import get_path
from .presets import apply_preset


def render_body(template: str, to: str, body: str) -> dict:
    """Substitui {{to}}/{{body}} no template JSON, com escape seguro, e parseia.

    Os placeholders devem aparecer dentro de strings JSON no template, ex.:
        {"number": "{{to}}", "text": "{{body}}"}
    """
    def esc(value: str) -> str:
        # json.dumps produz "\"...\""; removemos as aspas externas para inserir
        # o conteudo ja escapado dentro das aspas existentes do template.
        return json.dumps(value)[1:-1]

    rendered = template.replace("{{to}}", esc(to)).replace("{{body}}", esc(body))
    try:
        parsed = json.loads(rendered)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "WAQA_GENERIC_BODY_TEMPLATE nao e um JSON valido apos a substituicao "
            f"(verifique aspas em torno de {{{{to}}}}/{{{{body}}}}): {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ValueError("WAQA_GENERIC_BODY_TEMPLATE deve descrever um objeto JSON.")
    return parsed


class GenericProvider(WhatsAppProvider):
    def __init__(self, config: Config) -> None:
        apply_preset(config)
        self.config = config

        if not config.generic_send_url:
            raise ValueError("Provider generico requer WAQA_GENERIC_SEND_URL (ou um preset que a defina).")
        if not config.generic_body_template:
            raise ValueError("Provider generico requer WAQA_GENERIC_BODY_TEMPLATE (ou um preset que a defina).")

        try:
            import requests  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Provider generico requer o pacote 'requests' (pip install requests).") from exc
        self._requests = requests

        self._extra_headers: dict[str, str] = {}
        if config.generic_headers_json:
            try:
                self._extra_headers = dict(json.loads(config.generic_headers_json))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"WAQA_GENERIC_HEADERS deve ser um objeto JSON: {exc}") from exc

    def _auth(self, headers: dict[str, str], params: dict[str, str]):
        """Aplica autenticacao ao request; retorna a tupla de basic auth ou None."""
        cfg = self.config
        atype = (cfg.generic_auth_type or "none").lower()
        token = cfg.generic_auth_token
        if not token or atype == "none":
            return None
        if atype == "bearer":
            headers[cfg.generic_auth_header] = f"Bearer {token}"
        elif atype == "header":
            headers[cfg.generic_auth_header] = token
        elif atype == "query":
            params[cfg.generic_auth_query_param] = token
        elif atype == "basic":
            user, _, pwd = token.partition(":")
            return (user, pwd)
        # "path" ou outros: o token ja esta embutido na URL pelo usuario.
        return None

    def send_text(self, to: str, body: str) -> str:
        cfg = self.config
        headers: dict[str, str] = dict(self._extra_headers)
        params: dict[str, str] = {}
        auth = self._auth(headers, params)
        payload = render_body(cfg.generic_body_template, to, body)

        kwargs = {"headers": headers, "params": params, "timeout": 30}
        if auth:
            kwargs["auth"] = auth
        if (cfg.generic_content_type or "json").lower() == "form":
            kwargs["data"] = payload
        else:
            kwargs["json"] = payload

        resp = self._requests.request(cfg.generic_method or "POST", cfg.generic_send_url, **kwargs)
        if resp.status_code >= 400:
            raise RuntimeError(f"Gateway erro {resp.status_code}: {resp.text}")

        if cfg.generic_msg_id_path:
            try:
                mid = get_path(resp.json(), cfg.generic_msg_id_path)
                if mid is not None:
                    return str(mid)
            except ValueError:
                pass
        return "sent"

    def fetch_since(self, since: float) -> list[InboundMessage]:
        return read_since(self.config.inbox_path, since)
