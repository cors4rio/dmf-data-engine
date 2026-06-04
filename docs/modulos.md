# Catálogo de Módulos

> Inventário dos módulos ativos da Central DMF e dos seus serviços acoplados: responsabilidade, contrato de entrada e saída, dependências e padrão de integração aplicado.

---

## Sumário

1. [Como o Sistema Descobre Módulos](#1-como-o-sistema-descobre-módulos)
2. [Catálogo](#2-catálogo)
3. [Por Módulo](#3-por-módulo)
   - [AutomacaoHorasLauncher](#automacaohoraslauncher)
   - [FiscalModule](#fiscalmodule)
   - [DPModule](#dpmodule)
   - [ContabilModule](#contabilmodule)
   - [SemMovimentoNfseModule](#semmovimentonfsemodule)

---

## 1. Como o Sistema Descobre Módulos

O `ModuleRegistry` é o catálogo em memória da plataforma. Módulos são registrados explicitamente em `main.py` — não há descoberta automática por diretório.

O diagrama abaixo mostra o ciclo de vida completo de um módulo, do registro até a conclusão da execução.

```mermaid
graph TD
    REG["registry.register(MeuModulo(...))"]
    CAT["catalog()\n{setor: [meta_dict, ...]}"]
    UI["Frontend renderiza cards\npor setor e papel do usuário"]
    EXEC["registry.execute(module_id, opcoes)"]
    THREAD["ThreadRunner dispara\nexecute() em daemon thread"]
    PROG["Módulo emite events\nself.progress(pct, msg)"]
    BUS["EventBus → window.__onEvent"]
    DONE["execute() retorna {ok, ...}"]
    EVT["EventBus emite done\ncom resultado"]

    REG --> CAT
    CAT --> UI
    UI -->|"Usuário clica em Executar"| EXEC
    EXEC --> THREAD
    THREAD --> PROG
    PROG --> BUS
    THREAD --> DONE
    DONE --> EVT
    EVT --> BUS
```
![diagrama](img/modulos_1.svg)


**Responsabilidades do `ModuleRegistry`:**

| Método | Descrição |
|---|---|
| `register(module)` | Adiciona módulo ao catálogo em memória |
| `execute(module_id, opcoes)` | Despacha execução em thread separada; retorna `{"ok": True, "status": "running"}` imediatamente |
| `catalog()` | Retorna `{setor: [meta_dict, ...]}` para o JS renderizar os cards |
| `get_status(module_id)` | Retorna estado atual do módulo (idle/running) |

---

## 2. Catálogo

A Central DMF e seus serviços acoplados têm registries independentes. A Central registra apenas os launchers de serviços; cada serviço tem seu próprio registry com os módulos de negócio que lhe pertencem.

### Módulos da Central DMF

| ID | Nome | Setor | Papéis | Padrão | Localização |
|---|---|---|---|---|---|
| `automacao_horas` | Automação de Horas | GESTÃO | admin, contabil, fiscal, dp | Padrão B (subprocess + SSO) | `dmf_engine/modules/m_automacao_horas.py` |
| `relatorio_rendimentos` | Relatório de Rendimentos | CONTÁBIL | admin, contabil | Padrão 0 (inline) | `dmf_engine/modules/m_relatorio_rendimentos.py` |
| `sem_movimento_nfse` | Sem Movimento NFS-e Salvador | FISCAL | admin, fiscal | Padrão A (serviço + thread) | `dmf_engine/modules/m_sem_movimento_nfse.py` |

### Módulos da Automação de Horas (Serviço 1)

Registram-se no registry da própria Automação de Horas (`services/automacao_horas/`), não na Central DMF.

| ID | Nome | Setor | Papéis | Padrão | Localização |
|---|---|---|---|---|---|
| `fiscal` | Fiscal | FISCAL | admin, fiscal | Padrão A (Python externo) | `services/automacao_horas/modules/m_fiscal.py` |
| `dp` | Departamento Pessoal | DP | admin, dp | Padrão A (Python externo) | `services/automacao_horas/modules/m_dp.py` |
| `contabil` | Contábil | CONTABIL | admin, contabil | Padrão A (Python externo) | `services/automacao_horas/modules/m_contabil.py` |

> **Nota:** a lógica de negócio de `relatorio_rendimentos` fica em `services/relatorio_rendimentos/modulos/relatorio_rendimentos_isentos.py` e é importada diretamente pelo módulo da Central (sem processo separado).

---

## 3. Por Módulo

---

### AutomacaoHorasLauncher

**Arquivo:** `dmf_engine/modules/m_automacao_horas.py`

**Propósito:** Lançador da Automação de Horas a partir da Central DMF. Gera token SSO, despacha o processo Python 32-bit e aguarda o encerramento.

**Padrão aplicado:** Padrão B (subprocess) combinado com SSO por token. Consultar [design-patterns.md — SSO por Token](design-patterns.md#4-sso-por-token) e [design-patterns.md — Padrão B](design-patterns.md#6-padrão-b--binário-compilado).

**Entrada (`opcoes`):**

| Campo | Tipo | Descrição |
|---|---|---|
| — | — | Nenhum parâmetro externo; sessão é lida de `self.sessao()` |

**Saída:**

| Campo | Tipo | Descrição |
|---|---|---|
| `ok` | bool | `True` se o processo filho iniciou e encerrou sem erro |
| `erro` | str | Presente apenas se `ok = False` |

**Dependências:**

| Dependência | Tipo |
|---|---|
| `secrets`, `tempfile`, `subprocess` | Biblioteca padrão Python |
| `services/automacao_horas/main.py` | Processo filho (Python 32-bit) |
| `self.sessao()` | Sessão ativa da Central DMF |

**Fluxo resumido:**

1. Obtém sessão do usuário logado na Central.
2. Gera token aleatório (`secrets.token_hex(16)`).
3. Cria arquivo `dmf_session_<token>.json` em `temp/` com expiração de 30 segundos.
4. Lança `py -3-32 services/automacao_horas/main.py --session-token <token>`.
5. Retorna `{"ok": True}` quando o processo filho encerra.

---

### FiscalModule

**Arquivo:** `services/automacao_horas/modules/m_fiscal.py`

**Propósito:** Extrai horas fiscais do ERP Domínio via ODBC e injeta os valores calculados na coluna correspondente da planilha master.

**Padrão aplicado:** Padrão A — módulo Python com regras em `modulos/fiscal.py`, adaptado via BaseModule.

**Entrada (`opcoes`):**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `data_inicio` | str (ISO) | Sim | Início da competência fiscal (mês -2) |
| `data_fim` | str (ISO) | Sim | Fim da competência fiscal |
| `master_path` | str | Não | Caminho da planilha master (fallback: `config.json`) |

**Saída:**

| Campo | Tipo | Descrição |
|---|---|---|
| `ok` | bool | Sucesso da operação |
| `erro` | str | Mensagem de erro (presente se `ok = False`) |
| `tipo` | str | `"lock"` se o lock cooperativo foi negado |

**Dependências ativas (`services/automacao_horas/`):**

| Dependência | Descrição |
|---|---|
| `engine/database.py` | Conexão ODBC ao Sybase |
| `engine/master_writer.py` | Escrita na planilha master sem quebrar fórmulas |
| `engine/lock_master.py` | Lock cooperativo (adquire/libera `.dmflock`) |
| `modulos/fiscal.py` | Regras de negócio: GELOGUSER, adicional 80% |

**Notas:**

- A competência fiscal é mês -2 em relação ao mês corrente.
- O módulo adquire lock cooperativo antes de qualquer escrita. Libera no `finally`.
- O papel mínimo para executar é `fiscal` ou `admin`.

---

### DPModule

**Arquivo:** `services/automacao_horas/modules/m_dp.py`

**Propósito:** Calcula e injeta horas do Departamento Pessoal na planilha master. Executa em duas fases distintas: importação da planilha Carol e injeção na master.

**Padrão aplicado:** Padrão A — regras em `modulos/dp.py`, fluxo multifase controlado por `opcoes["fase"]`.

**Entrada (`opcoes`):**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `fase` | int | Sim | `1` = importar Carol (file dialog); `2` = injetar master |
| `master_path` | str | Não | Caminho da planilha master (fase 2) |
| `data_inicio` | str (ISO) | Sim (fase 2) | Início da competência DP (mês -1) |
| `data_fim` | str (ISO) | Sim (fase 2) | Fim da competência DP |

**Saída:**

| Campo | Tipo | Descrição |
|---|---|---|
| `ok` | bool | Sucesso da operação |
| `carol_path` | str | Caminho da planilha Carol selecionada (fase 1, se `ok`) |
| `erro` | str | Mensagem de erro (presente se `ok = False`) |
| `tipo` | str | `"lock"` se lock negado (fase 2) |

**Dependências ativas (`services/automacao_horas/`):**

| Dependência | Descrição |
|---|---|
| `engine/excel_parser.py` | Leitura da planilha Carol |
| `engine/master_writer.py` | Escrita na coluna Q da master |
| `engine/lock_master.py` | Lock cooperativo |
| `modulos/dp.py` | Regras de negócio: fórmula em cascata, exceções |

**Notas:**

- A fase 1 abre um `webview.create_file_dialog()` (síncrono) para o usuário selecionar a planilha Carol.
- A fase 2 usa o caminho da planilha selecionada na fase 1.
- A competência DP é mês -1 em relação ao mês corrente.
- O papel mínimo é `dp` ou `admin`.

---

### ContabilModule

**Arquivo:** `services/automacao_horas/modules/m_contabil.py`

**Propósito:** Processa horas contábeis em duas fases: extração do Domínio para planilha intermediária e injeção na master após validação manual da coluna R.

**Padrão aplicado:** Padrão A — regras em `modulos/contabil_preenchedor.py` e `modulos/contabil_integrador.py`, fluxo de 3 fases (2 automatizadas + 1 manual).

**Entrada (`opcoes`):**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `fase` | int | Sim | `2` = processar (ODBC → planilha intermediária); `5` = injetar master |
| `master_path` | str | Não | Caminho da planilha master (fase 5) |
| `data_inicio` | str (ISO) | Sim | Início da competência contábil (mês -1) |
| `data_fim` | str (ISO) | Sim | Fim da competência contábil |

**Saída:**

| Campo | Tipo | Descrição |
|---|---|---|
| `ok` | bool | Sucesso da operação |
| `arquivo_contabil` | str | Caminho de `HORAS CONTABEIS.xlsx` gerado (fase 2, se `ok`) |
| `erro` | str | Mensagem de erro (presente se `ok = False`) |
| `tipo` | str | `"lock"` se lock negado (fase 5) |

**Dependências ativas (`services/automacao_horas/`):**

| Dependência | Descrição |
|---|---|
| `engine/database.py` | Consulta ODBC ao Sybase |
| `engine/master_writer.py` | Escrita na coluna R da master |
| `engine/lock_master.py` | Lock cooperativo |
| `modulos/contabil_preenchedor.py` | Fase 2: ODBC → `HORAS CONTABEIS.xlsx` |
| `modulos/contabil_integrador.py` | Fase 5: Lê coluna R validada → master |

**Notas:**

- O fluxo contábil tem 3 fases: automática (fase 2) → manual (coluna R preenchida pelo usuário) → automática (fase 5).
- A fase 5 só deve ser executada após o usuário validar manualmente a planilha intermediária.
- A competência contábil é mês -1 em relação ao mês corrente.
- O papel mínimo é `contabil` ou `admin`.

---

---

### SemMovimentoNfseModule

**Arquivo:** `dmf_engine/modules/m_sem_movimento_nfse.py`
**Serviço acoplado:** `services/sem_movimento_nfse/`

**Propósito:** Automatiza a emissão dos comprovantes de **ausência de movimento de NFS-e** no portal municipal de Salvador (`nfse.salvador.ba.gov.br`) para um lote de empresas. Para cada empresa, gera dois PDFs (notas emitidas + notas recebidas como tomador) e um resumo consolidado em Excel.

**Padrão aplicado:** Padrão A — serviço em `services/` com thread dedicada, `threading.Event` para cancelamento e eventos via EventBus. O JS interage diretamente com métodos `sm_*` em `api.py`, não via `executar_modulo`.

**Estrutura do serviço:**

```
services/sem_movimento_nfse/
  sm_service.py          # thread/stop_flag/eventos — orquestrador
  sm_engine/
    sm_portal.py         # Playwright: login, extração de nome, emissão de PDF por empresa
    sm_captcha.py        # Anti-Captcha (ImageToTextTask) via HTTP puro
    sm_planilha.py       # parse TXT/xlsx com CNPJ + senha
    sm_resumo.py         # gera resumo consolidado .xlsx ao final do lote
```

**Entrada — `sm_executar(empresas_com_senha, mes, ano, pasta_destino)`:**

| Campo | Tipo | Descrição |
|---|---|---|
| `empresas_com_senha` | list | `[{"cnpj": str, "senha": str}, ...]` — lista com senhas reais (guardada em memória no JS) |
| `mes` | int | Mês da competência (1–12) |
| `ano` | int | Ano da competência |
| `pasta_destino` | str | Caminho da pasta onde os PDFs serão salvos |

**Saída — evento `sm_empresa` (por empresa processada):**

| Campo | Tipo | Descrição |
|---|---|---|
| `cnpj` | str | CNPJ da empresa (14 dígitos) |
| `status` | str | `"ok"`, `"erro"`, `"captcha_falhou"` |
| `emitidas` | dict | `{arquivo, qtd, status, detalhe}` |
| `recebidas` | dict | `{arquivo, qtd, status, detalhe}` — `status="sem_botao"` se empresa não tiver ponta de tomador |
| `detalhe` | str | Mensagem de erro (presente se `status != "ok"`) |
| `indice` | int | Posição da empresa no lote (1-based) |
| `total` | int | Total de empresas no lote |

**Saída — evento `sm_done` (ao final do lote):**

| Campo | Tipo | Descrição |
|---|---|---|
| `ok` | bool | `True` se zero erros |
| `total` | int | Total de empresas processadas |
| `ok_count` | int | Empresas concluídas com sucesso |
| `erros` | int | Empresas com erro ou captcha_falhou |
| `cancelado` | bool | `True` se o usuário cancelou via `sm_cancelar()` |
| `resumo_arquivo` | str\|None | Caminho do `resumo_sem_movimento_MMAAAA.xlsx` gerado |

**Nomenclatura dos PDFs gerados:**

```
{NomeEmpresa}_{6digitos_CNPJ}_{emitidas|recebidas}_{MMAAAA}.pdf
Exemplo: ACTION_SERVICOS_FINANCEIROS_LTDA_001-32_emitidas_052026.pdf
```

O nome da empresa é extraído automaticamente do `#ddlContribuinte` na tela de consulta do portal (campo disabled — lido via `page.evaluate()`).

**Configuração (chaves em `config.json`):**

| Chave | Tipo | Padrão | Descrição |
|---|---|---|---|
| `sm_anticaptcha_api_key` | str | `""` | Chave API do Anti-Captcha. Vazio = modo manual (usuário resolve no navegador) |
| `sm_headless` | bool | `true` | `false` força navegador visível (ignorado no modo manual, sempre visível) |
| `sm_captcha_timeout_s` | int | `60` | Timeout de polling do Anti-Captcha por empresa |
| `sm_pausa_entre_empresas_s` | float | `2` | Pausa interruptível entre empresas do lote |

**Métodos `api.py` expostos ao JS:**

| Método | Descrição |
|---|---|
| `sm_selecionar_planilha()` | Abre diálogo de arquivo (TXT ou xlsx) |
| `sm_carregar_planilha(caminho)` | Faz parse e retorna preview com senha mascarada (`****`) |
| `sm_executar(empresas_com_senha, mes, ano, pasta_destino)` | Inicia o lote em thread |
| `sm_executar_por_caminho(caminho, mes, ano, pasta_destino)` | Recarrega planilha e inicia lote (botão Recarregar) |
| `sm_cancelar()` | Sinaliza cancelamento via `stop_flag.set()` |
| `sm_get_status()` | Retorna `{status: "running"|"idle"}` |
| `sm_carregar_config()` | Lê configurações do `config.json` |
| `sm_salvar_config(dados)` | Salva configurações no `config.json` |
| `sm_abrir_template(tipo)` | Abre template de planilha (`"txt"` ou `"xlsx"`) com `os.startfile` |

**Dependências:**

| Dependência | Tipo |
|---|---|
| `playwright` (chromium) | Automação do portal (já instalado no projeto) |
| `requests` | Polling da API Anti-Captcha (HTTP puro, sem lib externa) |
| `openpyxl` | Leitura de `.xlsx` de entrada e geração do resumo |

**Notas:**

- Cada empresa usa um `BrowserContext` isolado (`new_context()`) — sem vazamento de sessão entre CNPJs.
- Modo manual (sem chave Anti-Captcha): força `headless=False`; timeout de 3 minutos por empresa para o usuário resolver o CAPTCHA.
- `status="sem_botao"` em `recebidas` não é erro — empresas sem atividade de tomador não têm o botão no portal. O PDF de emitidas é gerado normalmente.
- A senha nunca é logada nem persistida; é mascarada no preview da UI e trafega em memória apenas durante a execução do lote.
- O papel mínimo para executar é `fiscal` ou `admin`.

---

*Última atualização: 2026-06-04*
