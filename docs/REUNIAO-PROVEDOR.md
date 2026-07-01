# Guia da reuniao tecnica com o provedor de WhatsApp

Objetivo: sair da reuniao com os dados que faltam para o harness de teste falar
com o WhatsApp pela API/webhook do provedor. O programa ja esta pronto e cobre,
so por configuracao, os gateways mais comuns (ver tabela de cobertura). Na
reuniao normalmente basta escolher um preset e preencher URL + token.

## Contexto para alinhar com o provedor

- O nosso programa **nao** e um crawler de WhatsApp Web. Ele usa a API/webhook
  oficial do provedor, do jeito recomendado por eles.
- Ele atua como cliente: envia um roteiro de perguntas padrao para o nosso
  numero e confere se as respostas batem com o nosso checklist.
- Precisamos apontar o **webhook de mensagem recebida** do provedor para o nosso
  receptor (`python -m whatsapp_qa.webhook`), exposto numa URL publica.

## As 14 perguntas objetivas (cada uma vira uma configuracao)

1. Qual e a URL EXATA de envio de texto, ja com server-url/host/porta/instance/session preenchidos? -> `WAQA_GENERIC_SEND_URL`
2. Qual metodo HTTP e content-type do envio: JSON ou form-urlencoded? -> `WAQA_GENERIC_METHOD`, `WAQA_GENERIC_CONTENT_TYPE`
3. Como a credencial e enviada: Bearer no Authorization, header custom (qual nome?), token no path da URL, ou Basic usuario:senha? -> `WAQA_GENERIC_AUTH_TYPE` + `WAQA_GENERIC_AUTH_HEADER`
4. Qual e o token/api-key e de que nivel (instancia vs conta/global)? Ha um SEGUNDO segredo obrigatorio (ex.: Client-Token de conta na Z-API)? -> `WAQA_GENERIC_AUTH_TOKEN` + `WAQA_GENERIC_HEADERS`
5. Ha headers estaticos adicionais obrigatorios alem do de auth? -> `WAQA_GENERIC_HEADERS` (JSON)
6. Como e o corpo minimo para enviar um texto simples? Quais os NOMES exatos dos campos de destino e de texto (number/text, phone/message, to/Body, contents[].text)? -> `WAQA_GENERIC_BODY_TEMPLATE`
7. O numero de destino vai em formato puro (55DDD9...), E.164 com '+', ou com sufixo (@c.us / whatsapp:)? -> forma do `{{to}}` no body template
8. Na RESPOSTA de envio bem-sucedido, em qual campo vem o id da mensagem? -> `WAQA_GENERIC_MSG_ID_PATH`
9. Voces conseguem enviar um payload REAL de webhook de mensagem recebida (JSON literal capturado)? -> valida todos os `WAQA_GENERIC_INBOUND_*`
10. No webhook, em que caminho fica o TEXTO da mensagem? Ha caminho alternativo para links/citacao (ex.: extendedTextMessage.text)? -> `WAQA_GENERIC_INBOUND_TEXT_PATH`
11. Em que caminho fica o REMETENTE e ele vem como numero puro ou JID com '@'? -> `WAQA_GENERIC_INBOUND_FROM_PATH`
12. O webhook reentrega as mensagens que NOS enviamos (eco)? Se sim, ha flag booleana fromMe e em que caminho? Se nao, elas vem em evento/array separado? -> `WAQA_GENERIC_INBOUND_FROMME_PATH` (vazio se separado)
13. Qual a URL do endpoint de configuracao do webhook (e ha entrega por evento)? Precisamos apontar o receptor do harness la. -> operacional
14. Ha rate limit, janela de 24h ou obrigatoriedade de template para INICIAR conversa que impacte os testes? -> planejamento do harness

## Tabela de cobertura (gateways que ja suportamos por configuracao)

| Gateway | Preset | auth (header) | content-type | body (com {{to}}/{{body}}) | id na resposta | texto / remetente / fromMe |
|---|---|---|---|---|---|---|
| Evolution API (v2, Baileys) | `evolution` | header (`apikey`) | json | `{"number":"{{to}}","text":"{{body}}"}` | `key.id` | `data.message.conversation` / `data.key.remoteJid` / `data.key.fromMe` |
| WPPConnect Server | `wppconnect` | bearer (`Authorization`) | json | `{"phone":"{{to}}","message":"{{body}}"}` | `response.id` (validar) | `body` / `from` / `fromMe` |
| Z-API | `zapi` | header (`Client-Token`) + token na URL | json | `{"phone":"{{to}}","message":"{{body}}"}` | `messageId` | `text.message` / `phone` / `fromMe` |
| WhatsApp Cloud API (Meta) | `cloud` | bearer (`Authorization`) | json | corpo Meta (`text.body`) | `messages[0].id` | `entry[].changes[].value.messages[].text.body` / `...from` / (separado) |
| 360dialog | `360dialog` | header (`D360-API-KEY`) | json | corpo Meta (`text.body`) | `messages[0].id` | idem Meta |
| Twilio | `twilio` | basic (`SID:TOKEN`) | form | `{"To":"whatsapp:+{{to}}",...}` | `sid` | `Body` / `From` / (separado) |
| Gupshup | `gupshup` | header (`apikey`) | form | `message` = string JSON aninhada | `messageId` | `payload.payload.text` / `payload.sender.phone` / (separado) |
| Zenvia | `zenvia` | header (`X-API-TOKEN`) | json | `contents[].text` | `id` | `message.contents[].text` / `message.from` / (separado) |

Gateways baseados em WhatsApp Web (Evolution, WPPConnect, Z-API) reentregam
mensagens proprias com `fromMe=true` — o receptor ignora esses ecos. BSPs
oficiais (Cloud/360dialog/Twilio/Gupshup/Zenvia) entregam as enviadas em
eventos separados (statuses/status), entao nao geram eco no inbound.

Se o provedor nao for nenhum desses, tudo e configuravel por
`WAQA_GENERIC_*` — nao precisa de codigo novo, so das respostas das 14 perguntas.

## Depois da reuniao: como rodar

Ver o passo a passo em `whatsapp_qa/README.md` (secao "Provider generico") e o
`.env.example`. Fluxo resumido, ja com um preset:

```bash
export WAQA_PROVIDER=generic
export WAQA_GENERIC_PRESET=evolution        # ou zapi / wppconnect / ...
export WAQA_GENERIC_SEND_URL="https://SEU-SERVIDOR/message/sendText/SUA-INSTANCIA"
export WAQA_GENERIC_AUTH_TOKEN="APIKEY-DA-INSTANCIA"
export WAQA_TARGET_NUMBER=552133861504
export ANTHROPIC_API_KEY=...                # a chave ja usada no chama-project

# receptor do webhook (numa URL publica, ex. via ngrok) para captar as respostas:
python -m whatsapp_qa.webhook --port 8080

# rodar o roteiro:
python -m whatsapp_qa run --checklist checklists/1rcpn_respostas.yaml --format md --out relatorio.md
```

Consulte `python -m whatsapp_qa presets` para ver todos os presets e caminhos.
