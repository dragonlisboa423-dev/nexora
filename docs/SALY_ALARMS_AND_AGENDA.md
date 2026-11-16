# Agenda e alarmes persistentes

A Agenda preserva as tarefas anteriores e acrescenta eventos, visualizações dia/semana/mês/lista, prévia de conflitos, edição, exclusão e recorrência. Datas são normalizadas em UTC com fuso IANA; horários inexistentes ou ambíguos exigem correção. Recorrências suportam regras limitadas diárias, semanais, mensais e anuais. Dias inexistentes no mês são pulados. A prévia de conflitos cobre os próximos 90 dias, sem prometer detectar colisões infinitas.

Alarmes independentes ou associados a eventos compartilham um agendador no backend, executado a cada 15 segundos. Estado e ocorrências ficam no banco. A identidade determinística de cada ocorrência impede duplicação pelo reinício do servidor. Eventos movidos reagendam seus alarmes associados; exclusão cancela os pendentes. Alertas vencidos há mais de cinco minutos são registrados como perdidos, sem alegação de entrega retroativa.

A interface precisa estar aberta, autenticada e com avisos permitidos para buscar ocorrências. Sons precisam de interação explícita para liberar áudio. Voz usa o mecanismo selecionado e disponível. Solicitar Notification não comprova exibição pelo sistema operacional: o histórico registra `ui_reported`, solicitação de áudio/voz e apresentação separadamente. Recarregar restaura o aviso sem repetir o som. Há adiamento e conclusão. Claims temporários reduzem repetição entre abas, mas não garantem entrega física exatamente uma vez após falhas de rede.

**Web Push, alarme nativo Android e horário exato com navegador fechado não estão configurados.** O backend parado não agenda entregas. Alarmes novos ainda não fazem parte da fila offline do cofre; tarefas antigas continuam no protocolo já testado. Consulte `/api/notifications/capabilities` para estado observado.

Ferramentas do agente consultam relógio e eventos/alarmes. Escritas exigem aprovação e ficam vinculadas à versão revisada. O adaptador Core passou para 1.1.0 para orientar o uso do relógio em datas relativas e não prometer Push; o JSON original foi preservado.

```bash
bash scripts/install.sh
SALY_SECURE_COOKIE=1 bash scripts/start.sh
.venv/bin/python -m pytest backend/tests/test_planning.py -q
.venv/bin/python scripts/browser_planning.py
```

No Codespaces HTTPS, permita notificações se desejar, habilite os avisos em Alarmes e use os testes. O teste de apresentação cria ocorrência persistente real; não comprova funcionamento com aba fechada. Scripts de navegador usam servidor/banco descartáveis, sem consumir Groq.

O cofre agora oferece cópia opcional de eventos, alarmes e ocorrências para consulta offline. Atualiza ao sincronizar. Essa cópia não entrega notificações nem agenda disparos no aparelho; edição de eventos/novos alarmes permanece online.
