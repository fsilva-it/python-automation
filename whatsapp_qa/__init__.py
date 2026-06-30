"""whatsapp_qa - harness de teste automatizado para assistentes de WhatsApp.

Envia uma bateria de mensagens pre-prontas (checklist) para um numero/bot de
WhatsApp, captura as respostas e avalia cada uma contra o criterio esperado,
gerando um relatorio de aprovado/reprovado.

Arquitetura:
    providers/  - camada de transporte (Cloud API, Twilio, mock local)
    checklist   - carga e validacao dos casos de teste (YAML/JSON)
    grader      - avaliacao da resposta (palavra-chave, IA, exato)
    runner      - orquestra o ciclo enviar -> aguardar -> avaliar
    report      - renderiza o resultado (console / json / markdown)
"""

__version__ = "0.1.0"
