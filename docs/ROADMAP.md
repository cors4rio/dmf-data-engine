# Roadmap

> Visão consolidada do que vem a seguir: backlog técnico, decisões em aberto e próximos serviços candidatos.

---

## Sumário

1. [Plataforma em Expansão](#1-plataforma-em-expansão)
2. [Backlog Técnico](#2-backlog-técnico)
3. [Limpeza das Dependências Residuais da Central](#3-limpeza-das-dependências-residuais-da-central)
4. [Pós-Piloto — Distribuição](#4-pós-piloto--distribuição)
5. [Próximos Serviços Candidatos](#5-próximos-serviços-candidatos)
6. [Decisões em Aberto](#6-decisões-em-aberto)

---

## 1. Plataforma em Expansão

A Central DMF deixou de ser a "ferramenta de horas" e passou a ser uma plataforma que hospeda múltiplos serviços. A Automação de Horas é o primeiro serviço acoplado. O diagrama abaixo ilustra a trajetória.

```mermaid
graph TD
    NOW["Agora — v0.2.0\nCentral DMF + Automação de Horas\nPiloto em produção (5 usuários)"]
    NEXT["Próximas semanas\nEstabilização do piloto\nLimpeza das dependências residuais\nDecisão de distribuição"]
    POST["Pós-Piloto\nDecisão Inno Setup vs .bat\nNovos serviços candidatos\nExpansão de usuários"]

    NOW --> NEXT --> POST
```

O posicionamento como plataforma é a decisão arquitetural mais importante da v0.2.0 — ela define que qualquer novo serviço setorial seguirá o mesmo padrão de launcher + SSO, sem alterar a plataforma central.

---

## 2. Backlog Técnico — Automação de Horas (Serviço 1)

> Backlog do primeiro serviço. Melhorias na infraestrutura da plataforma Central DMF estão documentadas na Seção 3 (limpeza de dependências residuais).

### Epic 1 — Módulo Contábil: Refinamento

- **Integração real do Contábil**: substituir o comportamento de simulação (`scratch/integrar_contabil_onedrive.py`) pelo conector real do OneDrive/SharePoint na interface.
- **Mapeamento de Peso Múltiplo**: implementar a regra de peso métrico por lançamento (ex.: 0.5 min por lançamento) e presença de extrato (`orig_lan=39`).
- **Validação de Sincronia**: garantir que a leitura da aba `MM.AAAA` valide se os dados do cliente batem com o CNPJ do Domínio antes de confirmar.

### Epic 2 — Módulo Fiscal: Estabilização

- **Tratamento de Dados Nulos**: queries ODBC que retornem `NULL` ou tempos não computados não podem quebrar a injeção na planilha.
- **Revisão da Regra dos 80%**: validar se o acréscimo está refletindo corretamente na coluna O para todos os `GELOGUSER`.
- **Limpeza de Fantasmas**: assegurar que clientes sem horas fiscais no mês atual tenham o registro zerado (remover resíduos do mês anterior).

### Epic 3 — UI: Polimento

- **Exibição Dinâmica do Log**: parsear o log em tempo real na tela de Relatório (hoje só mostra status final).
- **Tratamento de Exceções na Tela**: pop-up amigável quando a planilha master estiver aberta por outro usuário.

### Em Validação

- **Resiliência da Planilha Master**: testes do `master_writer.py` para garantir que o preenchimento não quebre as fórmulas complexas (coluna R, totais) do `.xlsm`.
- **Filtros de Parâmetros na UI**: validar se competência e acréscimos salvos pelo usuário estão sendo aplicados nas queries.
- **Lock Cooperativo Multi-usuário**: simular dois supervisores em paralelo e validar a mensagem amigável de "Outro usuário está gravando".

---

## 3. Migração para 64-bit Unificado ✅ CONCLUÍDA (2026-06)

> Mantido como registro de decisão. A migração foi implantada — a Central e a Automação de Horas rodam em Python 64-bit, no mesmo processo.

**Contexto:** acreditava-se que as dependências da Central em `engine/` (raiz) obrigavam Python 32-bit. Investigação (2026-06) provou que era falso: a restrição vinha *apenas* do acesso ao banco via o DSN ODBC "Contabil", registrado como 32-bit no Windows. O SAP SQL Anywhere 17 tem driver 64-bit, e a conexão **DSN-less** (`DRIVER=SQL Anywhere 17;...`) funciona em 64-bit.

**O que foi feito:**
- Camada de banco migrada para DSN-less (DRIVER + host + porta), sem DSN por máquina.
- Central movida para Python 64-bit.
- Automação de Horas embutida como launcher **in-process** (Padrão 0) — eliminados subprocesso, token SSO por arquivo e a infra 32-bit triplicada.

➡️ Detalhes técnicos preservados em [`legacy/migracao-64bit.md`](legacy/migracao-64bit.md).

---

## 4. Pós-Piloto — Distribuição

Após o piloto com os usuários reais (um por setor + admin), avaliar a forma de distribuição.

### Opção A — Inno Setup (instalador `.exe` único)

- Empacota `dist/DMF Engine/` em um único `Setup_DMF_Engine.exe`.
- Aparece em "Adicionar/Remover Programas".
- Atalhos automáticos no Menu Iniciar + Área de Trabalho.
- Suporta uninstall limpo e versionamento (mostra delta de versão).
- Permite assinatura digital para silenciar o SmartScreen.

### Opção B — Manter o `.bat` Aprimorado

- Sem nova dependência de ferramenta externa.
- Acrescentar arquivo `VERSION` em `_internal/`.
- O `.bat` compara a versão instalada com a da rede e informa o delta.
- Notificação dentro do dashboard quando nova versão estiver disponível.

**Critério de decisão:** se os 5 usuários conseguirem usar o `.bat` sem fricção, manter Opção B. Se houver atrito (usuários que não encontram o `.bat`, que não entendem "instalar", ou se o sistema expandir para mais usuários), migrar para Opção A.

---

## 5. Módulos Ativos na Central DMF

| Módulo | Setor | Status | Notas |
|---|---|---|---|
| `automacao_horas` | Administrativo | Produção (piloto) | Launcher in-process 64-bit (Padrão 0) — migração concluída (ver Seção 3) |
| `relatorio_rendimentos` | Contábil | Produção | Padrão 0 inline |
| `buscar_xml` | Fiscal | Produção | Padrão A (projeto externo `bx_*` + motor TOKAI) |
| `sem_movimento_nfse` | Fiscal | Produção | Padrão A, Anti-Captcha, Playwright |
| `tff_salvador` | Legalização | Produção | Padrão A, Playwright (4 guias TFF + TLL) |

---

## 6. Próximos Serviços Candidatos

| Serviço | Descrição | Padrão de Integração |
|---|---|---|
| `buscador_xml` | Busca e processamento de XMLs fiscais | Padrão A (Python externo) |
| Novos setores | Legalização, Consultoria, outros setores da DMF | Módulos dentro da Automação ou novo serviço |
| Dashboard consolidado | Visão executiva de produtividade (exportação PDF/Excel) | Módulo UI na Central |

Cada novo serviço deve seguir o padrão estabelecido: launcher na Central + serviço em `services/` + eventos via EventBus.

---

## 7. Decisões em Aberto

| Decisão | Contexto | Critério |
|---|---|---|
| Inno Setup vs `.bat` | Distribuição pós-piloto | Feedback dos 5 usuários do piloto |
| Repositório único vs separado para novos serviços | Hoje: tudo no mesmo repo | Serviço com ciclo de vida independente → repo separado |
| ~~Migração para 64-bit unificado~~ | **Resolvido (2026-06):** implantada — ver Seção 3 e [`legacy/migracao-64bit.md`](legacy/migracao-64bit.md) | — |
| ~~Exposição da API da Automação~~ | **Resolvido:** com 64-bit unificado a Automação vira módulo inline; não precisa de API entre processos | — |

---

*Última atualização: 2026-06-18*
