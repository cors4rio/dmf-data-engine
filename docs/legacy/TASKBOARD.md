# Painel de Tarefas Geral — DMF Engine (Kanban)

Mapeia as frentes de trabalho do projeto: demandas de negócio (Fiscal, Contábil, DP) e técnicas (Arquitetura, UI, Distribuição).

---

## A FAZER (To Do)

### Epic 1: Módulo Contábil — Refinamento
- [ ] **Integração Real do Contábil**: substituir o comportamento de simulação (`scratch/integrar_contabil_onedrive.py`) na interface para chamar o conector real do OneDrive/SharePoint.
- [ ] **Mapeamento de Peso Múltiplo**: implementar a regra de peso métrico por lançamento (ex.: 0.5 min por lancto) e presença de extrato (`orig_lan=39`).
- [ ] **Validação de Sincronia**: garantir que a leitura da aba "MM.AAAA" valide se os dados do cliente bateram com o CNPJ do Domínio antes de confirmar.

### Epic 2: Módulo Fiscal — Estabilização
- [ ] **Tratamento de Dados Nulos**: queries ODBC do Sybase no Fiscal que retornem `NULL` ou tempos não computados não podem quebrar a injeção na planilha.
- [ ] **Revisão da Regra dos 80%**: validar se o acréscimo de +80% no tempo bruto está refletindo corretamente na coluna O da Master para todos os `GELOGUSER`.
- [ ] **Limpeza de 'Fantasmas'**: assegurar que clientes sem horas fiscais no mês atual tenham o registro zerado na planilha (remover resíduo do mês anterior).

### Epic 3: UI — Polimento
- [ ] **Exibição Dinâmica do Log**: parsear o log em tempo real na tela de "Relatório" (hoje só mostra status final).
- [ ] **Tratamento de Exceções na Tela**: pop-up amigável quando o `CONTROLE DE HORAS DMF.xlsm` estiver aberto por outro usuário (locked file).

---

## EM ANDAMENTO (Doing)

- [ ] **Piloto com os 5 usuários reais**: Carol, James, Nayane, Jailton, Adriele rodando o sistema em produção por ~1 mês. Coleta de feedback diário no início.

---

## EM TESTE / VALIDAÇÃO (Review)

- [ ] **Gravação e Resiliência da Planilha Master**: testes do `master_writer.py` para garantir que o preenchimento não quebre as fórmulas complexas (coluna R, totais) do `.xlsm`.
- [ ] **Filtros de Parâmetros na UI**: validar se os parâmetros (competência, acréscimos percentuais) salvos pelo usuário estão de fato sendo aplicados nas queries do Domínio.
- [ ] **Lock cooperativo multi-usuário**: simular dois supervisores rodando módulos em paralelo e validar que o segundo recebe mensagem amigável de "Outro usuário está gravando".

---

## PÓS-PILOTO (Após 1 mês de uso real)

> Avaliar a forma de distribuição com base no feedback dos 5 usuários. Detalhamento no [DISTRIBUICAO.md, seção 8](DISTRIBUICAO.md#8-roadmap-pós-piloto-1-mês-de-uso-real).

- [ ] **Decisão A vs B**: manter o fluxo `Instalar DMF Engine.bat` (Opção B) ou migrar para instalador `.exe` único via **Inno Setup** (Opção A).
- [ ] **Se Inno Setup**: criar `installer.iss`, gerar `Setup_DMF_Engine.exe`, registrar no "Adicionar/Remover Programas", configurar uninstall limpo, considerar assinatura digital para silenciar o SmartScreen.
- [ ] **Se manter `.bat`**: acrescentar arquivo `VERSION` em `_internal\`, fazer o `.bat` comparar com a versão instalada e mostrar o delta, notificar o usuário dentro do dashboard quando subir versão nova na rede.
- [ ] **Re-treino dos usuários**: se mudar a forma de instalar, atualizar o `GUIA_USUARIO.md` e o conteúdo no Anytype.

---

## CONCLUÍDO (Done)

### Empacotamento e Distribuição
- [x] **Geração do executável**: PyInstaller (`dmf_engine.spec`) gerando `.exe` standalone modo `onedir`, sem janela de terminal, com ícone embarcado.
- [x] **Build script único**: `build.bat` na raiz — limpa, empacota, copia templates de exceção e o instalador.
- [x] **Instalador local para usuário leigo**: `Instalar DMF Engine.bat` copia o app de `\\rede\` para `%LOCALAPPDATA%\DMF Engine\` via `robocopy /XO`, preservando estado local, e cria atalho na área de trabalho com `IconLocation` explícito.
- [x] **Frozen mode (`sys.frozen`)**: `dmf_engine/main.py` separa `BASE_DIR` (escrita) de `RESOURCES_DIR` (assets em `_internal\`); `modulos/excecoes.py` resolve `config\nao_faz_setor\` dinamicamente.
- [x] **Ícone na taskbar e no atalho**: `SetCurrentProcessExplicitAppUserModelID` + ícone embarcado no `.exe` + `IconLocation` no `.lnk` + invalidação do cache via `ie4uinit -show`.
- [x] **Limpeza da raiz do projeto**: removidos `automacao.py`, `build_runner.py`, `debug_planilhas.py`, `format_guide.py`, `GUIA_USUARIO_FORMATADO.md`, `anonymize.ps1`, `log_execucao.md`, `SQL.LOG`, `SQL_UTF8.LOG`, `LOOG_APP.jpeg`, `resultado_consumo_unidades_1261.csv`, `relatorio_contabil_05.2026.md`, `build_log.txt`. Liberou ~50 MB.

### Arquitetura e UI
- [x] **PyWebView como UI escolhida**: descartado o Flet (`interface_supervisor.py`), unificado em `dmf_engine/main.py`.
- [x] **Bridge Python ↔ JS**: endpoints reais (não simulados) ligando o `index.html` ao backend.
- [x] **Dashboard funcional**: 5 métricas + 4 gráficos (Chart.js) — horas por setor, top clientes, preenchimento por setor, distribuição por hora — com drill-down.

### Multi-usuário e Segurança
- [x] **5 usuários fixos + admin**: Carol (admin), James (contábil), Nayane (fiscal), Jailton (DP), Adriele (legalização). Sem UI de auto-cadastro.
- [x] **Permissões por papel**: cada papel só executa o módulo do próprio setor; Carol executa todos.
- [x] **Hash de senha PBKDF2-SHA256** + salt (120k iterações, salt 16 bytes), sem reversão.
- [x] **Machine binding**: vincula a senha à máquina (hostname + USERNAME) no primeiro login.
- [x] **Tela de login limpa**: removida a listagem de nomes de usuários (não vazar quem usa).
- [x] **Lock cooperativo**: gravações na master usam lock atômico (`open('x')`) com expiração de 5 min, na pasta do OneDrive.
- [x] **Estado compartilhado**: JSON ao lado da master registra "quem rodou o quê e quando" — visível para todos.
- [x] **Link "Guia de uso"** na tela de login abrindo o conteúdo do Anytype.

### Regras de Negócio
- [x] **Competência por módulo**: DP e Contábil usam mês -1 da data atual; Fiscal usa mês -2.
- [x] **Conexão ODBC**: DSN `Contabil` (Sybase SQL Anywhere 32-bit) validada e estável.
- [x] **DP — Lógica base**: cálculo da Planilha Carol, ponderando ativos vs sócios (`(ativos × 0.33) + 1.5h`).
- [x] **Fiscal — Acréscimo de 80%**: aplicado no tempo bruto antes de gravar na coluna O.
- [x] **Contábil — 3 fases**: Anexar → Preencher F/I/O em `HORAS CONTABEIS.xlsx` → Lançar coluna R na master.
- [x] **Exceções por setor**: `DP_NAO.txt`, `CONTABIL_NAO.txt`, `FISCAL_NAO.txt` em `config\nao_faz_setor\` — `modulos/excecoes.py` é a fonte única de leitura.

### Observabilidade
- [x] **Logs separados**: `dmf_engine.log` (INFO+) e `dmf_engine_errors.log` (WARNING+) com `sys.excepthook` capturando uncaught exceptions.
- [x] **Log estruturado em Markdown**: `log_execucao.md` gerado por ciclo (descontinuado — substituído pelo estado compartilhado).

### Documentação
- [x] **`GUIA_USUARIO.md`**: guia em português sem jargão técnico, publicado no Anytype.
- [x] **`DISTRIBUICAO.md`**: guia operacional de build e distribuição (este projeto).
- [x] **`Specs_Definitivos/`**: regras de negócio detalhadas por setor (Fiscal, DP, Contábil, Master).
