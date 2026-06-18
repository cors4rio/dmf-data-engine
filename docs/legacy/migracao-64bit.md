# Guia de Implantação — Migração para 64-bit Unificado

> **Status: CONCLUÍDA (2026-06).** Documento histórico, preservado como registro da
> decisão e da implantação. A Central e o `automacao_horas` já rodam em Python 64-bit,
> no mesmo processo, com conexão DSN-less. O texto abaixo descreve o estado *anterior*
> à migração e os passos executados — não é mais um plano pendente.

## Por que esta migração

Hoje a Central e o `automacao_horas` rodam em **Python 32-bit** por uma única razão:
o acesso ao banco do Domínio usa o **DSN ODBC "Contabil"**, que está registrado como
32-bit no Windows. Toda a complexidade do projeto (subprocesso separado, infra
triplicada, pendência de empacotar um segundo `.exe`) deriva dessa amarra.

**A amarra é artificial.** O banco é **SAP SQL Anywhere 17**, que tem driver 64-bit
já instalado na máquina (`SQL Anywhere 17\Bin64\dbodbc17.dll`). Conectar em 64-bit
foi **testado e funciona** — basta trocar a conexão por DSN-less (sem depender do
DSN do Windows). Ver memória de projeto `bitness-32-e-falso`.

### O que foi comprovado (rede interna, Python 64-bit)

```
DSN-less 64-bit → versao=17.0.11.7312 | db=contabil   ✅ CONECTOU
```

| Cenário | 32-bit | 64-bit |
|---|---|---|
| via `DSN=Contabil` | ✅ | ❌ (DSN é 32-bit: erro IM014) |
| **DSN-less** (`DRIVER=SQL Anywhere 17;...`) | ✅ | ✅ **← o caminho** |

---

## Pré-requisitos de ambiente (já satisfeitos nas máquinas atuais)

- **Driver 64-bit instalado:** `C:\Program Files\SQL Anywhere 17\Bin64\dbodbc17.dll`
  (verificar com: `Test-Path "C:\Program Files\SQL Anywhere 17\Bin64\dbodbc17.dll"`).
- Driver ODBC "SQL Anywhere 17" registrado (aparece em `pyodbc.drivers()` no 64-bit).
- Banco acessível por TCP/IP na rede interna: `192.168.25.102:2638`, server `srvlinux`,
  database `contabil`.

> ⚠️ Se uma máquina não tiver o `Bin64`, instalar o runtime do SQL Anywhere 17 64-bit
> (ou o pacote completo da SAP). É a única dependência de máquina nova.

---

## Connection string validada (a peça central)

```
DRIVER=SQL Anywhere 17;ENG=srvlinux;DBN=contabil;LINKS=TCPIP{host=192.168.25.102;serverport=2638};UID=EXTERNO;PWD=<senha>
```

- **UID correto é `EXTERNO`** — não `dba`. (O `config.json` hoje tem `db_uid=dba`, que o
  banco rejeita. Corrigir para `EXTERNO`.)
- Host/porta/server devem vir do `config.json`, não hardcoded — ver passo 1.

---

## Passos de implantação

### Passo 0 — Validar conexão 64-bit na rede de produção (5 min)

Antes de mudar código, rodar este teste numa máquina de produção (rede interna),
com Python 64-bit:

```python
import pyodbc
cs = ("DRIVER=SQL Anywhere 17;ENG=srvlinux;DBN=contabil;"
      "LINKS=TCPIP{host=192.168.25.102;serverport=2638};UID=EXTERNO;PWD=<senha>")
c = pyodbc.connect(cs, timeout=10)
print(c.cursor().execute("SELECT @@version, db_name()").fetchone())
```

Resultado esperado: `('17.0.11.7312', 'contabil')`. Se falhar com `-100`, é rede
(servidor/rota). Se `-103`, é credencial (confirmar UID=EXTERNO + senha).

### Passo 1 — Migrar a camada de banco para DSN-less

Arquivos com a conexão ODBC (todos montam `DSN={dsn};UID=...;PWD=...`):
- `engine/database.py` (Central / raiz)
- `services/automacao_horas/engine/database.py`

Trocar a montagem de `connection_string` de `DSN=...` para a string DSN-less acima,
lendo `host`, `port`, `server`, `database`, `uid`, `pwd` do `config.json`. Adicionar
essas chaves ao `DEFAULTS` do ConfigManager (`dmf_engine/core/config.py`) com os
valores conhecidos como default. Manter compatibilidade: se uma chave `db_dsn` ainda
existir e `db_host` não, pode cair no modo DSN (fallback) durante a transição.

Sugestão de chaves novas no config:
```
"db_driver": "SQL Anywhere 17",
"db_server": "srvlinux",
"db_host":   "192.168.25.102",
"db_port":   2638,
"db_database":"contabil",
"db_uid":    "EXTERNO",      # corrigir de "dba"
```

### Passo 2 — Validar tudo ainda em 32-bit

DSN-less funciona **também** em 32-bit (testado). Então: aplicar o Passo 1, rodar
`py -3-32 dmf_engine\main.py` e o `automacao_horas`, e confirmar que as queries do
Domínio continuam funcionando. Isso isola a mudança de conexão da mudança de bitness.

### Passo 3 — Migrar a Central para 64-bit

Com a conexão já DSN-less e sem dependência de driver 32-bit:
1. Instalar as dependências (pyodbc, openpyxl, pywebview, etc.) num Python **64-bit**.
2. Trocar `py -3-32` por `py` (64-bit) nos comandos de dev (`CLAUDE.md`, `run.bat`).
3. Rodar a Central em 64-bit e exercitar os módulos que tocam o banco.

### Passo 4 — Embutir o automacao_horas como módulo inline (Padrão 0)

Com tudo 64-bit, o `automacao_horas` **não precisa mais** de subprocesso separado:
- Converter `AutomacaoHorasLauncher` (launcher `sync` que abre subprocesso) em um
  `BaseModule` inline, como o `BuscarXMLModule`. A UI vira tela interna na Central
  (substituição de tela), não janela própria — já validado como aceitável.
- Remover o token SSO por arquivo (`dmf_session_*.json`): a sessão já está no processo.
- Renomear os pacotes do `automacao_horas` para namespace próprio (`ah_engine`,
  `ah_core`, etc.) para não colidir com a raiz — ver memória `colisao-pacotes-engine-config`.

### Passo 5 — Simplificar o build

- Sem subprocesso, **não há segundo `.exe`** para empacotar. Um único `DMF Engine.exe`
  64-bit contém tudo. A pendência de "empacotar automacao_horas.exe" deixa de existir.
- Ajustar `dmf_engine.spec` / `build_runner.py` para o Python 64-bit.

---

## Verificação final (end-to-end)

1. Central abre em 64-bit (`py dmf_engine\main.py`).
2. Módulo de Horas abre como **tela interna** e executa Fiscal/DP/Contábil — queries no
   Domínio retornam dados reais (conexão 64-bit DSN-less).
3. Buscar XML e Relatório de Rendimentos seguem funcionando.
4. Build gera **um** `.exe` 64-bit; rodar o `.exe` numa máquina limpa (com o driver
   SQL Anywhere 17 64-bit) e repetir os testes.

---

## O que esta migração elimina

- A amarra de 32-bit (a causa de toda a complexidade de processos separados).
- A dependência de um **DSN configurado no Windows** de cada máquina (DSN-less resolve).
- O **subprocesso** do automacao_horas e a classe de bugs "launcher síncrono via thread"
  (ver memória `launcher-automacao-horas`).
- A **infra triplicada** (`core`/`modules`/`engine`/`ConfigManager` × 3) — colapsa numa só.
- A pendência de **empacotar um segundo `.exe`** para produção.
