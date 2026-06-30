# whatsapp_qa - teste automatizado de assistente de WhatsApp por checklist

Harness que envia uma bateria de mensagens pre-prontas para um numero/bot de
WhatsApp, captura as respostas e avalia cada uma contra o criterio esperado do
seu checklist, gerando um relatorio de aprovado/reprovado.

## Como funciona

```
checklist (YAML/JSON)
        |
        v
   runner  --send-->  provider  --WhatsApp-->  BOT SOB TESTE
        ^                 |
        |             resposta (via webhook -> inbox)
        |                 |
     grader <-------------+
        |
        v
    relatorio (console / json / markdown)
```

O harness atua como "cliente": envia para o numero do bot e aguarda a resposta
que o bot devolve. Os casos rodam em sequencia para preservar a ordem das
respostas.

## Providers (camada de transporte)

| provider | uso | observacao |
| --- | --- | --- |
| `mock`   | desenvolvimento/demonstracao | bot simulado em memoria, sem WhatsApp real, sem credencial, sem custo |
| `cloud`  | producao (recomendado) | WhatsApp Cloud API oficial da Meta |
| `twilio` | producao | Twilio API for WhatsApp |

> Bibliotecas nao-oficiais (whatsapp-web.js, Baileys) violam os Termos da Meta e
> tem risco de banimento do numero. Por isso o harness so traz caminhos oficiais.

## Instalacao

O provider `mock` + avaliacao por palavra-chave/exato rodam **so com a
biblioteca padrao**. Para os demais recursos:

```bash
pip install -r whatsapp_qa/requirements.txt
```

## Uso rapido (demonstracao, sem WhatsApp real)

```bash
python -m whatsapp_qa run --checklist checklists/exemplo.yaml
```

## Formato do checklist

Lista de casos em YAML ou JSON. Campos por caso:

| campo | obrigatorio | descricao |
| --- | --- | --- |
| `id` | sim | identificador unico |
| `send` | sim | mensagem enviada ao bot |
| `expect_keywords` | um criterio* | palavras/expressoes que devem aparecer (ignora acento/caixa) |
| `expect` | um criterio* | criterio em linguagem natural (avaliado por IA) |
| `expect_exact` | um criterio* | resposta exata esperada |
| `grader` | nao | forca a estrategia do caso: `keyword`/`exact`/`ai` |
| `category` | nao | agrupamento no relatorio |

\* defina ao menos um dos tres criterios.

Valide o arquivo sem enviar nada:

```bash
python -m whatsapp_qa validate --checklist checklists/exemplo.yaml
```

### Checklist real do 1º RCPN-RJ

`checklists/1rcpn_respostas.yaml` foi gerado a partir do documento oficial
*RESPOSTAS PADRONIZADAS — OFICIAL (rev. 2)*: 55 casos, cada um com a pergunta do
cliente e a resposta esperada fiel a fonte, avaliados por IA (`grader: ai`).

```bash
ANTHROPIC_API_KEY=... WAQA_PROVIDER=cloud WAQA_TARGET_NUMBER=552133861504 \
python -m whatsapp_qa run --checklist checklists/1rcpn_respostas.yaml --format md --out relatorio.md
```

## Avaliacao (grader)

- `keyword` - aprova se todas as palavras-chave aparecem (deterministico, sem custo)
- `exact` - aprova se a resposta normalizada bate exatamente
- `ai` - usa Claude para julgar se a resposta atende ao criterio em linguagem natural
- `hybrid` (padrao) - tenta keyword/exact e recorre a IA nos casos com `expect`

## Rodando contra WhatsApp real

### 1. WhatsApp Cloud API (Meta)

```bash
export WAQA_PROVIDER=cloud
export WAQA_CLOUD_PHONE_NUMBER_ID=...        # id do numero remetente (do harness)
export WAQA_CLOUD_ACCESS_TOKEN=...
export WAQA_TARGET_NUMBER=5511999999999      # numero do bot sob teste (E.164)
export ANTHROPIC_API_KEY=...                 # opcional, para o grader 'ai'

# 1) Suba o receptor de webhook (numa porta publica/tunel) para captar as respostas:
python -m whatsapp_qa.webhook --port 8080 --verify-token SEU_TOKEN
#    configure a URL https publica + SEU_TOKEN no painel da Meta.

# 2) Rode a bateria:
python -m whatsapp_qa run --checklist checklists/meu.yaml --format md --out relatorio.md
```

### 2. Twilio

```bash
export WAQA_PROVIDER=twilio
export WAQA_TWILIO_ACCOUNT_SID=...
export WAQA_TWILIO_AUTH_TOKEN=...
export WAQA_TWILIO_FROM="whatsapp:+14155238886"
export WAQA_TARGET_NUMBER=5511999999999
# Aponte o webhook de mensagem recebida da Twilio para o mesmo python -m whatsapp_qa.webhook
python -m whatsapp_qa run --checklist checklists/meu.yaml
```

## Variaveis de ambiente

| variavel | padrao | descricao |
| --- | --- | --- |
| `WAQA_PROVIDER` | `mock` | `mock` / `cloud` / `twilio` |
| `WAQA_TARGET_NUMBER` | - | numero do bot sob teste (E.164, so digitos) |
| `WAQA_GRADER` | `hybrid` | `keyword` / `exact` / `ai` / `hybrid` |
| `WAQA_REPLY_TIMEOUT` | `30` | espera maxima (s) pela resposta de cada caso |
| `WAQA_PAUSE_BETWEEN` | `2` | pausa (s) entre casos |
| `WAQA_INBOX_PATH` | `whatsapp_qa_inbox.jsonl` | arquivo de inbox preenchido pelo webhook |
| `WAQA_CLOUD_PHONE_NUMBER_ID` | - | Cloud API |
| `WAQA_CLOUD_ACCESS_TOKEN` | - | Cloud API |
| `WAQA_CLOUD_API_VERSION` | `v21.0` | Cloud API |
| `WAQA_TWILIO_ACCOUNT_SID` | - | Twilio |
| `WAQA_TWILIO_AUTH_TOKEN` | - | Twilio |
| `WAQA_TWILIO_FROM` | - | Twilio (`whatsapp:+...`) |
| `WAQA_ANTHROPIC_API_KEY` / `ANTHROPIC_API_KEY` | - | grader `ai` |
| `WAQA_ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | modelo do grader `ai` |

## Codigo de saida

`run` retorna `0` se todos os casos passaram, `1` se algum reprovou e `2` em erro
de configuracao/checklist - pronto para uso em CI.

## Testes

```bash
python -m unittest discover -s tests
```

## Notas de conformidade

- Apenas canais oficiais (Cloud API / Twilio); nenhum segredo fica no codigo
  (tudo via ambiente).
- Fora da janela de atendimento de 24h, a Cloud API exige mensagens do tipo
  *template* aprovadas - planeje o checklist conforme essa regra.
