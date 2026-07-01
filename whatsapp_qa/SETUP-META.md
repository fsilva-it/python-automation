# Guia de configuracao - WhatsApp Cloud API (Meta)

Passo a passo para rodar o harness contra um WhatsApp atendido pela Cloud API da
Meta. Quem executa precisa de acesso ao app no Meta for Developers.

## Conceito-chave: dois numeros

O harness atua como um **cliente**. Existem dois numeros envolvidos:

- **Numero do harness (remetente):** um numero registrado na Cloud API, do qual
  o harness envia as mensagens de teste. E o `WAQA_CLOUD_PHONE_NUMBER_ID`.
- **Numero do bot (alvo):** o WhatsApp que esta sendo testado, que recebe as
  perguntas e responde. E o `WAQA_TARGET_NUMBER`.

As respostas do bot chegam ao **webhook** configurado para o numero do harness.
O receptor (`python -m whatsapp_qa.webhook`) grava essas respostas numa inbox que
o harness le para avaliar.

> Se o numero do bot tambem for da Cloud API no mesmo app, o webhook recebe os
> dois lados; o harness considera apenas o texto recebido (as respostas do bot).

## Passos

### 1. Obter as credenciais

No painel Meta for Developers > seu App > WhatsApp > API Setup:

- **Phone number ID** do numero remetente -> `WAQA_CLOUD_PHONE_NUMBER_ID`
- **Access token** -> `WAQA_CLOUD_ACCESS_TOKEN`
  (para uso continuo, gere um token de System User de longa duracao em
  Business Settings > Users > System Users.)

### 2. Subir o webhook em uma URL publica

A Meta so entrega eventos para uma URL HTTPS publica. Em desenvolvimento, use um
tunel (ex.: ngrok):

```bash
set -a; source .env; set +a
python -m whatsapp_qa.webhook --port 8080 --verify-token UM_TOKEN_FORTE
# em outro terminal:
ngrok http 8080      # copie a URL https publica gerada
```

### 3. Registrar o webhook na Meta

No painel > WhatsApp > Configuration:

- **Callback URL:** `https://SEU_TUNEL/webhook`
- **Verify token:** o mesmo `UM_TOKEN_FORTE` do passo 2
- Assine o campo **messages**.

A Meta faz um GET de verificacao; o receptor responde ao desafio
(`hub.challenge`) automaticamente.

### 4. Janela de atendimento de 24h

Fora de uma conversa ativa, a Cloud API so permite enviar **templates**
aprovados. Para um teste de QA com texto livre, garanta que o numero do bot
tenha iniciado/respondido uma conversa nas ultimas 24h, ou adapte o checklist
para usar templates. (O harness atual envia texto; o suporte a template pode ser
adicionado ao provider `cloud` se necessario.)

### 5. Rodar a bateria

```bash
set -a; source .env; set +a
python -m whatsapp_qa run \
  --checklist checklists/1rcpn_respostas.yaml \
  --format md --out relatorio.md
```

O relatorio fica em `relatorio.md`. O codigo de saida e `0` se todos os casos
passaram, `1` se algum reprovou.

## Solucao de problemas

- **Nenhuma resposta capturada (timeout):** confirme que o webhook esta acessivel
  publicamente e assinado em `messages`; verifique se a inbox
  (`WAQA_INBOX_PATH`) esta sendo escrita quando o bot responde.
- **Erro 401/403 no envio:** token expirado ou sem permissao
  `whatsapp_business_messaging`.
- **Erro de janela/template:** veja o passo 4.
- **`grader 'ai' indisponivel`:** defina `ANTHROPIC_API_KEY` e instale o pacote
  `anthropic` (`pip install -r whatsapp_qa/requirements.txt`).
