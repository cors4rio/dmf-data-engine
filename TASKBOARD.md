# 📋 Painel de Tarefas Geral — DMF Data Engine (Kanban)

Este painel mapeia todas as frentes de trabalho do projeto, organizando as demandas de negócio (Fiscal, Contábil, DP) e técnicas (Arquitetura, UI).

---

## 🟩 A FAZER (To Do)

### 📌 Epic 1: Módulo Contábil (Finalização e Automação Direta)
- [ ] **Integração Real do Contábil**: Substituir o comportamento de simulação (`scratch.integrar_contabil_onedrive`) na interface para chamar o conector real do OneDrive/Sharepoint.
- [ ] **Mapeamento de Peso Múltiplo**: Implementar a regra de peso métrico por lançamento (ex: 0.5 min por lancto) e presença de extrato (orig_lan=39).
- [ ] **Validação de Sincronia**: Garantir que a leitura da aba "04.2026" (ou mês vigente) valide se os dados do cliente bateram com o CNPJ do Domínio.

### 📌 Epic 2: Módulo Fiscal (Estabilização)
- [ ] **Tratamento de Dados Nulos**: Garantir que consultas ODBC do Sybase no Fiscal que retornem Null ou tempos não computados não quebrem a injeção na planilha.
- [ ] **Revisão da Regra dos 80%**: Validar se a matemática do acréscimo de +80% no tempo bruto está refletindo corretamente na coluna O da Master para todos os usuários (`GELOGUSER`).
- [ ] **Limpeza de 'Fantasmas'**: Assegurar que clientes sem horas fiscais no mês atual tenham seu registro de horas zerado na planilha (removendo resíduos do mês passado).

### 📌 Epic 3: Interface Gráfica (Supervisor UI)
- [ ] **Decisão e Unificação de UI**: Escolher entre Flet (`interface_supervisor.py`) e PyWebView (`dmf_engine/main.py`) e descartar a versão rejeitada.
- [ ] **Exibição Dinâmica do Log**: Fazer com que o `log_execucao.md` seja renderizado ou parseado visualmente na tela de "Relatório" da UI.
- [ ] **Tratamento de Exceções na Tela**: Adicionar pop-ups amigáveis se o `CONTROLE DE HORAS DMF.xlsm` estiver aberto por outro usuário (erro de locked file).

### 📌 Epic 4: DevOps, Empacotamento e Arquitetura
- [ ] **Limpeza da Raiz do Projeto**: Mover as pastas soltas (`engine/`, `modulos/`) para dentro de `dmf_engine/` e mover scripts utilitários (`debug_planilhas.py`, `anonymize.ps1`) para uma pasta `scripts/`.
- [ ] **Geração do Executável**: Configurar o `pyinstaller` ou spec file para gerar o `.exe` standalone, permitindo que a aplicação rode sem Python instalado.
- [ ] **Centralização do Entrypoint**: Criar um arquivo único `run.py` para iniciar a aplicação, encerrando a duplicidade de chamadas.

---

## 🟨 EM ANDAMENTO (Doing)

- [ ] **Desenvolvimento da Interface Flet**: Criação do dashboard visual com Flet (`interface_supervisor.py`), conectando botões às funções do backend. *(Atualmente em fase de mock/simulação na aba Contábil).*

---

## 🟦 EM TESTE / VALIDAÇÃO (Review)

- [ ] **Gravação e Resiliência da Planilha Master**: Testes do `master_writer.py` para garantir que o preenchimento não quebre as fórmulas complexas (Coluna R, Totais) do arquivo `.xlsm`.
- [ ] **Filtros de Parâmetros na UI**: Validar se os parâmetros (ex: Competência, acréscimos percentuais) salvos pelo usuário estão de fato sendo aplicados nas queries do Banco Domínio.

---

## 🟩 CONCLUÍDO (Done)

- [x] **Conexão ODBC Base**: Driver do Sybase configurado e testado para conectar no BD Domínio.
- [x] **Lógica Base do Departamento Pessoal (DP)**: Cálculo funcional da "Planilha Carol", ponderando ativos vs sócios ((ativos × 0.33) + 1.5h).
- [x] **Geração Inicial de Log (log_execucao.md)**: Sistema base de gravação de sucessos/erros por módulo implementado em Markdown.
- [x] **Especificações Documentadas**: Regras de negócio detalhadas (Fiscal, DP, Contábil, Master) estabelecidas na pasta `Specs_Definitivos`.
