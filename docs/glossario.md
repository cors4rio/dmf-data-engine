# Glossário do Domínio

> Definições dos termos técnicos e de negócio usados na Central DMF e nos seus serviços. Consultar quando encontrar um termo desconhecido na documentação ou no código.

---

**Adaptador de Módulo**
Arquivo Python em `modules/m_<nome>.py` que conecta a lógica de negócio ao sistema de plugins. Herda `BaseModule` e é registrado no `ModuleRegistry`. Não contém regras de negócio — delega para `modulos/`.

**BaseModule**
Classe abstrata (ABC) que define o contrato de todos os módulos da Central DMF. Todo módulo deve implementar a propriedade `meta` (retorna `ModuleMeta`) e o método `execute(opcoes)`. Localizada em `dmf_engine/modules/base.py` e copiada em `services/automacao_horas/modules/base.py`.

**Central DMF**
Componente de plataforma do sistema: interface gráfica (PyWebView), autenticação, plugin system e orquestração de módulos. Roda em Python 64-bit. Corresponde ao diretório `dmf_engine/`. É o nome oficial do aplicativo.

**CNPJ Duplicado**
Situação em que o mesmo CNPJ aparece em mais de uma linha da planilha master. Indica erro de cadastro (empresa aberta novamente, ou registrada com dois códigos Domínio diferentes). O sistema alerta no log e não preenche automaticamente nenhuma das linhas.

**Código Domínio (`codi_emp`)**
Identificador numérico de um cliente no ERP Domínio Sistemas. Usado como primeira variável de lookup na planilha master (coluna H). Alguns clientes possuem textos especiais no lugar do código numérico.

**Competência**
Mês de referência dos dados processados. Difere do mês de execução por setor: Fiscal usa mês -2; DP e Contábil usam mês -1. Ver [regras-de-negocio.md — Conceito de Competência](regras-de-negocio.md#1-conceito-de-competência).

**Controle de Empregados (Planilha do DP)**
Planilha `.xls` de entrada manual produzida mensalmente pelo setor de DP com o número de empregados ativos por empresa. Usada como fonte de dados para o módulo DP. Não é extraída automaticamente do Domínio — é um arquivo entregue pelo setor.

**Contrato de Retorno**
Convenção de que todo `execute()` retorna `dict` com a chave `ok: bool`. O JS lê essa chave para exibir sucesso ou erro. Ver [design-patterns.md — Contrato de Retorno](design-patterns.md#10-contrato-de-retorno).

**DMF (escritório)**
Escritório de contabilidade DMF Contabilidade — o cliente interno para o qual o sistema foi construído. Todos os usuários são colaboradores internos da DMF.

**DMFLock (`.dmflock`)**
Arquivo criado atomicamente no OneDrive para sinalizar que a planilha master está em uso. A operação `open(path, 'x')` é atômica no Windows. Ver [design-patterns.md — Lock Cooperativo](design-patterns.md#3-lock-cooperativo).

**Domínio (ERP)**
Sistema ERP Domínio Sistemas (da Benner), usado pelo escritório DMF para registro de horas, folha de pagamento e contabilidade dos clientes. O banco de dados é SAP SQL Anywhere 17, acessado via ODBC 64-bit em modo DSN-less.

**EventBus**
Canal único de comunicação Python → JavaScript. Todos os módulos emitem eventos via `EventBus.emit(module_id, event, data)` em vez de chamar `window.evaluate_js()` diretamente. O JS recebe tudo via `window.__onEvent`. Ver [design-patterns.md — EventBus](design-patterns.md#2-eventbus--comunicação-python--js).

**Exceção por Setor**
Empresa que não realiza determinado serviço na DMF (ex: empresa com sistema próprio). Gerenciada via arquivos de texto em `config/nao_faz_setor/`. Ver [operacoes.md — Gestão de Exceções](operacoes.md#9-gestão-de-exceções-por-setor).

**Frozen Mode**
Estado do executável compilado com PyInstaller. Detectado via `getattr(sys, 'frozen', False)`. Em frozen mode, assets ficam em `sys._MEIPASS` (somente leitura) e arquivos de estado ficam no diretório do `.exe`. Ver [design-patterns.md — Frozen Mode](design-patterns.md#8-frozen-mode).

**GELOGUSER**
Tabela de auditoria central do ERP Domínio (`bethadba.geloguser`). Registra cada sessão de acesso de colaboradores ao sistema por módulo (`sist_log`). Fonte dos dados do Módulo Fiscal (`sist_log = 5`).

**Lookup Duplo**
Algoritmo de identificação de cliente na planilha master que tenta primeiro pelo Código Domínio (coluna H) e, como fallback, pelo CNPJ (coluna J). Garante que clientes sem código numérico (valores especiais em H) ainda sejam localizados. Ver [regras-de-negocio.md — Lookup Duplo](regras-de-negocio.md#2-planilha-master).

**Machine Binding**
Mecanismo de segurança que vincula a senha de um usuário à máquina específica onde fez login pela primeira vez (hostname + USERNAME). Impede uso da mesma credencial em outra máquina sem reconfiguração.

**Master (Planilha Master)**
Arquivo `CONTROLE DE HORAS DMF.xlsm` no OneDrive corporativo. Produto final da automação — consolidação mensal de horas por cliente e setor. Ver [regras-de-negocio.md — Planilha Master](regras-de-negocio.md#2-planilha-master).

**ModuleMeta**
Dataclass Python com os metadados de identidade de um módulo: `id`, `nome`, `desc`, `setor`, `icon`, `color`, `papeis`, `status`. Usada pelo `ModuleRegistry` para construir o catálogo e pelo frontend para renderizar os cards.

**ModuleRegistry**
Catálogo em memória que armazena todos os módulos registrados e despacha execuções via `ThreadRunner`. Expõe `catalog()` para o frontend renderizar os cards por setor. Ver [modulos.md — Como o Sistema Descobre Módulos](modulos.md#1-como-o-sistema-descobre-módulos).

**ODBC**
Open Database Connectivity — interface padrão para conexão com bancos de dados. A Automação de Horas usa ODBC 64-bit para conectar ao SAP SQL Anywhere 17 (ERP Domínio). A conexão é **DSN-less** (`DRIVER=SQL Anywhere 17;Host=...;Port=...`): basta o driver 64-bit instalado, sem DSN registrado por máquina.

**OneDrive**
Serviço de armazenamento corporativo da Microsoft, usado para sincronizar a planilha master e o arquivo de lock entre as máquinas dos supervisores.

**PBKDF2-SHA256**
Algoritmo de hash de senha com salt e 120.000 iterações, usado para armazenar as senhas em `supervisores.json`. Não é reversível — a senha original nunca é recuperável a partir do hash.

**Plataforma vs Serviço**
A Central DMF é a **plataforma** (infraestrutura, UI, autenticação, plugin system). A Automação de Horas é o primeiro **serviço** acoplado à plataforma. Essa distinção orienta decisões arquiteturais sobre onde colocar código novo.

**Plugin System**
Arquitetura que permite adicionar módulos à Central DMF sem editar o código existente. Composto por `BaseModule` (contrato), `ModuleMeta` (identidade) e `ModuleRegistry` (catálogo + dispatch). Ver [design-patterns.md — Plugin System](design-patterns.md#1-plugin-system--basemodule-modulemeta-moduleregistry).

**SSO por Token** *(retirado)*
Mecanismo histórico: enquanto a Automação de Horas rodava como subprocesso 32-bit, a Central transferia a sessão por um token JSON temporário em `temp/` (validade 30s, uso único). Removido na unificação 64-bit — o serviço agora roda in-process e reaproveita a sessão diretamente. Ver [design-patterns.md — Sessão Compartilhada](design-patterns.md#4-sessão-compartilhada-substitui-o-antigo-sso-por-token).

---

*Última atualização: 2026-05-29*
