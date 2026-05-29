# Spec: Produtividade do Setor Fiscal (Escrita Fiscal)
> **Projeto:** N8N Automação — DMF Contabilidade
> **Versão:** 1.0
> **Última atualização:** 2026-03-11
> **Responsável técnico:** Ícaro Conceição
> **Validado em:** Janeiro/2026 — empresas 1227, 696, 129, 466 confirmaram os valores cravados com o relatório do sistema Domínio.

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Fontes de Dados](#2-fontes-de-dados)
   - 2.1 [Banco de Dados Domínio (Sybase/ODBC)](#21-banco-de-dados-domínio-sybasedbc)
   - 2.2 [Sistema Gestta — EXCLUÍDO](#22-sistema-gestta--excluído)
3. [Pipeline de Processamento](#3-pipeline-de-processamento)
4. [Query SQL Principal — Validada](#4-query-sql-principal--validada)
5. [Regras de Cálculo de Tempo](#5-regras-de-cálculo-de-tempo)
6. [Estrutura da Planilha Master](#6-estrutura-da-planilha-master)
7. [Tabelas e Campos Chave — Módulo Fiscal (Domínio)](#7-tabelas-e-campos-chave--módulo-fiscal-domínio)
8. [Conectividade ODBC](#8-conectividade-odbc)
9. [Gotchas e Armadilhas do Banco Domínio](#9-gotchas-e-armadilhas-do-banco-domínio)
10. [Scripts e Arquivos do Projeto](#10-scripts-e-arquivos-do-projeto)
11. [Fluxograma do Processo](#11-fluxograma-do-processo)
12. [Problemas Conhecidos e Soluções (Troubleshooting)](#12-problemas-conhecidos-e-soluções-troubleshooting)

---

## 1. Visão Geral

O **módulo de Produtividade Fiscal** captura o tempo real que cada colaborador da DMF passou trabalhando dentro do sistema Domínio especificamente no módulo de **Escrita Fiscal** (código 5). Esse dado alimenta a coluna **O — Horário Fiscal** da **Planilha Mestre de Controle de Horas** (`CONTROLE_DE_HORAS_DMF.xls`).

### Contexto na Planilha Master

| Coluna Excel | Setor | Fonte |
|---|---|---|
| **O — Horário Fiscal** | **Escrita Fiscal** | **Banco Domínio (GELOGUSER) ← ESTE SPEC** |
| P — Horário Contábil | Contabilidade | Planilha HORAS CONTABEIS (.xlsx) |
| Q — Horário Pessoal | Folha de Pagamento (DP) | Planilha Controle Empregados + Domínio |
| R — Total | Soma O+P+Q | Fórmula Excel `=O+P+Q` |

> **Nota histórica:** Antes desta automação, a coluna O era alimentada manualmente via relatório exportado do sistema Gestta (`.xls`). A partir de Janeiro/2026, passou a ser extraída **diretamente do banco Domínio via SQL**, aumentando a precisão e eliminando dados do Gestta.

---

## 2. Fontes de Dados

### 2.1 Banco de Dados Domínio (Sybase/ODBC) ⭐ Fonte Primária

O sistema ERP **Domínio Sistemas** (Benner) registra toda a atividade dos usuários em uma tabela de auditoria chamada `GELOGUSER`. Cada vez que um colaborador abre uma empresa em um módulo específico, é gerado um registro com horário de início e fim da sessão.

#### Parâmetros de Conexão

| Parâmetro | Valor |
|---|---|
| **Protocolo** | ODBC (Driver SQL Anywhere / Sybase) |
| **DSN Padrão** | `Contabil` |
| **Usuário** | `EXTERNO` |
| **Schema** | `bethadba` |

> ⚠️ **Segurança:** A senha nunca deve ser exposta em logs, código versionado ou mensagens. Utilize variáveis de ambiente ou arquivo `.env` não versionado.

---

### 2.2 Sistema Gestta — EXCLUÍDO ❌

> **O tempo do Gestta não deve ser contabilizado no Horário Fiscal.**

O Gestta é uma plataforma de gestão de tarefas e rotinas (diferente da produtividade dentro do ERP Domínio). O tempo registrado no Gestta corresponde a tarefas administrativas e de controle, **não ao tempo de escrita fiscal efetiva** dentro do sistema contábil.

A extração direta do `GELOGUSER` com filtro `sist_log = 5` já exclui automaticamente quaisquer atividades fora do Domínio.

---

## 3. Pipeline de Processamento

```
┌─────────────────────────────────────────────────────────────┐
│                PIPELINE DE PRODUTIVIDADE FISCAL             │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────┐
  │  1. Query Banco Domínio (ODBC) — VALIDADA JAN/2026  │
  │     SELECT usua_log, codi_emp, SUM(DATEDIFF(second)) │
  │     FROM bethadba.geloguser                          │
  │     WHERE sist_log = 5                               │
  │     AND tfim_log IS NOT NULL                         │
  │     AND data_log BETWEEN 'INICIO' AND 'FIM'          │
  │     GROUP BY usua_log, codi_emp                      │
  │     Ref: QUERY_tempo_gasto_fiscal.md                 │
  └───────────────────┬──────────────────────────────────┘
                      │   segundos_por_colaborador_e_empresa
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  2. Agregar por Cliente (codi_emp)                   │
  │     Somar segundos de TODOS os colaboradores         │
  │     por empresa no período                           │
  │     Converter: segundos → HH:MM:SS                   │
  └───────────────────┬──────────────────────────────────┘
                      │   dict_fiscal {codi_emp → segundos_brutos}
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  3. Aplicar Adicional de 80%                       │
  │     segundos_final = segundos_brutos × 1.80          │
  │     Razão: overhead de deslocamento e apoio          │
  │     que não é capturado pelo log do sistema           │
  └───────────────────┬──────────────────────────────────┘
                      │   dict_fiscal {codi_emp → segundos_final}
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  4. Preencher Planilha Master (coluna O)             │
  │     CONTROLE_DE_HORAS_DMF.xls (Aba MM.AAAA)         │
  │     Match por: codi_emp (col H) ou nome (cols I/K)   │
  └───────────────────┬──────────────────────────────────┘
                      │
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  5. Atualizar Total (coluna R)                       │
  │     Fórmula Excel: =O{row}+P{row}+Q{row}            │
  │     Formato: [h]:mm:ss                               │
  └──────────────────────────────────────────────────────┘
```

---

## 4. Query SQL Principal — Validada

Esta é a query definitiva, validada contra o relatório oficial do Domínio em Janeiro/2026. Os resultados bateram **cravados** (precisão de segundos).

> **Arquivo de referência:** [`QUERY_tempo_gasto_fiscal.md`](./QUERY_tempo_gasto_fiscal.md)

```sql
-- ============================================================
-- PRODUTIVIDADE FISCAL — Query Validada (Jan/2026)
-- Precisão: SEGUNDOS (obrigatório para bater com o Domínio)
-- ============================================================

SELECT 
    l.usua_log              AS Colaborador,
    e.codi_emp              AS Codigo_Cliente,
    e.nome_emp              AS Nome_Cliente,
    SUM(
        DATEDIFF(second,                              -- ← SEGUNDOS, não minutos!
            YMD(YEAR(l.data_log),  MONTH(l.data_log),  DAY(l.data_log))  + l.tini_log,
            COALESCE(
                YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log,
                YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log
            )
        )
    ) AS Total_Segundos_Fiscal
FROM 
    bethadba.geloguser l
INNER JOIN 
    bethadba.geempre e ON e.codi_emp = l.codi_emp
WHERE 
    l.sist_log = 5           -- ← Código 5 = 'Escrita Fiscal'
    AND l.tfim_log IS NOT NULL  -- ← Exclui sessões sem encerramento (crash/desconexão)
    AND l.data_log >= '2026-01-01'
    AND l.data_log <= '2026-01-31'
    -- AND l.codi_emp IN (466, 129)  ← Filtro opcional por empresa
    -- AND l.usua_log IN ('ANALISTA.FISCAL1', 'GERENTE.FISCAL')  ← Filtro opcional por colaborador
GROUP BY 
    l.usua_log,
    e.codi_emp,
    e.nome_emp
ORDER BY 
    e.codi_emp,
    Total_Segundos_Fiscal DESC;
```

### Conversão do Resultado em Python

```python
# Converter segundos acumulados para HH:MM:SS
def segundos_para_hms(total_segundos: int) -> str:
    """
    Converte um total de segundos inteiros para o formato HH:MM:SS.
    
    Args:
        total_segundos: Total de segundos acumulados da sessão do colaborador.
    
    Returns:
        String no formato 'HH:MM:SS'.
    """
    h = total_segundos // 3600
    m = (total_segundos % 3600) // 60
    s = total_segundos % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# Fator de adicional obrigatório: 80% sobre o tempo bruto do Domínio
FATOR_ADICIONAL_FISCAL = 1.80

# Converter para fração de dia (formato interno do Excel)
def segundos_para_excel(total_segundos: int, aplicar_adicional: bool = True) -> float:
    """
    Converte segundos para o valor fracionário de dia usado pelo Excel,
    aplicando o adicional de 80% obrigatório ao tempo bruto do Domínio.
    Após inserir na célula, formatar como [h]:mm:ss.
    
    Args:
        total_segundos: Total de segundos brutos acumulados (saída da query SQL).
        aplicar_adicional: Se True (padrão), multiplica por FATOR_ADICIONAL_FISCAL (1.80).
    
    Returns:
        Float representando a fração do dia (1.0 = 24h), já com o adicional aplicado.
    """
    segundos_final = total_segundos * FATOR_ADICIONAL_FISCAL if aplicar_adicional else total_segundos
    return segundos_final / 86400.0  # 86400 = 60 * 60 * 24
```

---

## 5. Regras de Cálculo de Tempo

### 5.1 Adicional de 80% (Fator Obrigatório) ⭐

> **REGRA DE NEGÓCIO:** O tempo extraído do Domínio representa apenas o tempo que o colaborador ficou logado dentro da empresa no sistema. Existe um overhead real de comunicação, alinhamento, correções e suporte que **não é capturado pelo sistema**. Por isso, aplica-se um adicional de **80%** sobre o tempo bruto antes de gravar na planilha master.

```
tempo_final = tempo_bruto_dominio × 1.80
```

**Exemplo prático:**

| Tempo Bruto (Domínio) | × 1.80 | Tempo Final (Planilha O) |
|---|---|---|
| 00:10:00 (600 seg) | × 1.80 | 00:18:00 (1080 seg) |
| 00:30:00 (1800 seg) | × 1.80 | 00:54:00 (3240 seg) |
| 01:00:00 (3600 seg) | × 1.80 | 01:48:00 (6480 seg) |
| 02:00:00 (7200 seg) | × 1.80 | 03:36:00 (12960 seg) |

> ⚠️ O adicional é aplicado **por empresa** (sobre o total já somado de todos os colaboradores), não por sessão individual.

```python
FATOR_ADICIONAL_FISCAL = 1.80

# Calcular tempo final por empresa
for codi_emp, total_segundos_bruto in dict_fiscal.items():
    segundos_final = int(total_segundos_bruto * FATOR_ADICIONAL_FISCAL)
    valor_excel = segundos_final / 86400.0  # Fração de dia para o Excel
    # Gravar valor_excel na coluna O da linha correspondente ao cliente
```

### 5.2 Precisão: Segundos (Regra de Extração) ⭐

> **CRÍTICO:** O sistema Domínio acumula os **segundos brutos** de cada sessão antes de converter para o formato de horas do relatório. Qualquer cálculo em **minutos** causará arredondamentos e os valores **não vão bater** com o relatório oficial.

| Abordagem | Resultado |
|---|---|
| `DATEDIFF(minute, ...)` | ❌ Arredonda para cima/baixo — valores divergem |
| `DATEDIFF(second, ...)` | ✅ Precisão exata — valores cravados com o Domínio |

**Validação realizada em Janeiro/2026:**
| Cliente | Código | Domínio (oficial) | Nossa Extração (seconds) | Status |
|---|---|---|---|---|
| EMPRESA EXEMPLO ALPHA EIRELI | 1227 | 00:18:44 | 00:18:44 | ✅ Cravado |
| EMPRESA EXEMPLO BETA LTDA | 696 | 00:12:57 | 00:12:57 | ✅ Cravado |
| CLINICA EXEMPLO GAMA LTDA | 129 | 00:12:08 | 00:12:08 | ✅ Cravado |
| CLINICA EXEMPLO DELTA LTDA | 466 | 00:03:55 | 00:03:55 | ✅ Cravado |

### 5.2 Filtro de Sessões Limpas

Sessões onde `tfim_log IS NULL` representam:
- Crash ou reinicialização inesperada do sistema
- Desconexão de rede sem encerramento limpo
- Máquina travada

Essas sessões são **sempre descartadas** (`AND l.tfim_log IS NOT NULL`), pois não representam tempo produtivo real.

### 5.3 Filtro por Colaborador (Opcional)

A extração pode ser feita para:
- **Todos os colaboradores** (padrão para relatório completo)
- **Apenas colaboradores específicos** (uso do filtro `AND l.usua_log IN (...)`)

O campo `usua_log` armazena o **login de rede** do usuário (ex: `ANALISTA.FISCAL1`, `GERENTE.FISCAL`, `ANALISTA.FISCAL2`), não o nome completo. Ver seção de mapeamento na seção 7.

### 5.4 Tratamento de Sessões Cross-Midnight

Quando um colaborador trabalha passando da meia-noite (ex: início 23:50, fim 00:10 do dia seguinte), a tabela pode armazenar `dfim_log` diferente de `data_log`. Por isso usamos o `COALESCE` com dois timestamps:

```sql
COALESCE(
    YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log,  -- ← Data fim diferente
    YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log   -- ← Fallback: mesma data
)
```

---

## 6. Estrutura da Planilha Master

**Arquivo:** `CONTROLE_DE_HORAS_DMF.xls`
**Aba:** `MM.AAAA` (ex: `01.2026`)
**Dados começam na linha 10** (linhas 1-9 são cabeçalhos e configurações)

### Mapeamento de Colunas (openpyxl, 1-indexed)

| Nº Col. | Letra Excel | Nome do Campo | Tipo |
|---|---|---|---|
| 8 | H | **Código Domínio** (`codi_emp`) | Numérico |
| 9 | I | Nome Fantasia | Texto |
| 11 | K | Razão Social | Texto |
| 14 | N | **Mês Anterior - Fiscal** ← Backfill do mês anterior | Fração de dia (`[h]:mm:ss`) |
| 15 | O | **Horário Fiscal** ← Preenchido aqui (com adicional 80%) | Fração de dia (`[h]:mm:ss`) |
| 16 | P | Horário Contábil | Fração de dia |
| 17 | Q | Horário Pessoal (DP) | Fração de dia |
| 18 | R | Total (=O+P+Q) | Fórmula Excel |

### 6.1 Lógica de Match (Preenchimento da Coluna O)

A linha correta é identificada pelo **código Domínio** (`codi_emp`) na coluna H. Caso o código não seja encontrado, tenta-se o match por nome nas colunas I ou K.

```python
# Prioridade de match:
# 1º → Código Domínio (col H) — mais confiável
# 2º → Nome Fantasia (col I) — fallback
# 3º → Razão Social (col K) — fallback secundário
# Se nenhum match: empresa não está na planilha (cliente novo ou excluído)
```

### 6.2 Backfill do Mês Anterior (Coluna N) ⭐

> **Regra válida a partir de Dezembro/2025.** A partir deste mês, sempre que uma nova aba mensal for processada, deve-se copiar o valor da **coluna O (Horário Fiscal)** da **aba do mês anterior** para a **coluna N (Mês Anterior - Fiscal)** da aba do **mês atual**.

#### Lógica de Backfill

| Aba atual | Fonte | Destino |
|---|---|---|
| `01.2026` | Coluna O da aba `12.2025` | Coluna N da aba `01.2026` |
| `02.2026` | Coluna O da aba `01.2026` | Coluna N da aba `02.2026` |
| `MM.AAAA` | Coluna O da aba `MM-1.AAAA` | Coluna N da aba `MM.AAAA` |

#### Exemplo visual:

```
Aba 12.2025                         Aba 01.2026
┌─────────┬──────────┐              ┌──────────┬─────────┬───────────┐
│ Col H   │  Col O   │   ────────▶  │  Col H   │  Col N  │  Col O    │
│ codi_emp│ Fiscal   │   (copiar)   │ codi_emp │Ant.Fisc.│ Fiscal    │
├─────────┼──────────┤              ├──────────┼─────────┼───────────┤
│  1227   │ 00:31:54 │              │  1227    │ 00:31:54│ 00:18:44* │
│   696   │ 00:22:03 │              │   696    │ 00:22:03│ 00:12:57* │
└─────────┴──────────┘              └──────────┴─────────┴───────────┘
                                    * Valores já com adicional de 80%
```

#### Implementação Python

```python
def calcular_aba_anterior(mes: int, ano: int) -> str:
    """
    Retorna o nome da aba do mês anterior no formato 'MM.AAAA'.
    Trata a transição de ano (Janeiro → Dezembro do ano anterior).

    Args:
        mes: Mês atual (1-12).
        ano: Ano atual (ex: 2026).

    Returns:
        String no formato 'MM.AAAA' referente ao mês anterior.
    """
    if mes == 1:
        return f"12.{ano - 1}"
    return f"{mes - 1:02d}.{ano}"

def backfill_mes_anterior(wb_master, mes_atual: int, ano_atual: int) -> None:
    """
    Copia o valor da coluna O (Fiscal) da aba do mês anterior
    para a coluna N (Mês Anterior - Fiscal) da aba atual.

    Aplicação: Válida a partir de Dezembro/2025 (aba 12.2025 em diante).

    Args:
        wb_master: Objeto Workbook (openpyxl) da planilha master.
        mes_atual: Mês alvo do preenchimento (1-12).
        ano_atual: Ano alvo do preenchimento (ex: 2026).

    Raises:
        KeyError: Se a aba do mês anterior não existir na planilha.
    """
    aba_atual = f"{mes_atual:02d}.{ano_atual}"
    aba_anterior = calcular_aba_anterior(mes_atual, ano_atual)

    sh_atual = wb_master[aba_atual]
    sh_ant = wb_master[aba_anterior]

    # Mapear: codi_emp → valor coluna O do mês anterior
    valores_ant = {}
    for row in sh_ant.iter_rows(min_row=10):
        cod = row[7].value   # Coluna H (index 7) = codi_emp
        val = row[14].value  # Coluna O (index 14) = Fiscal
        if cod and val:
            valores_ant[cod] = val

    # Escrever na coluna N da aba atual
    for row in sh_atual.iter_rows(min_row=10):
        cod = row[7].value   # Coluna H = codi_emp
        if cod and cod in valores_ant:
            row[13].value = valores_ant[cod]  # Coluna N (index 13)
```

> ⚠️ Se a aba do mês anterior não existir (ex: primeiro uso do sistema), o backfill deve ser pulado sem erro.

---

## 7. Tabelas e Campos Chave — Módulo Fiscal (Domínio)

### 7.1 Tabela Principal: `bethadba.geloguser`

Esta é a tabela de auditoria central do Domínio. Registra cada sessão de acesso de qualquer usuário a qualquer módulo do sistema.

| Coluna | Tipo | Descrição |
|---|---|---|
| `nume_log` | INT | PK — Identificador único do registro de log |
| `codi_emp` | INT | FK → `geempre.codi_emp` — Código da empresa acessada |
| `usua_log` | VARCHAR | **Login de rede do colaborador** (ex: `ANALISTA.FISCAL1`) |
| `sist_log` | INT | **Código do módulo** (ver tabela de módulos abaixo) |
| `data_log` | DATE | Data de início da sessão |
| `tini_log` | TIME | Horário de início da sessão |
| `tfim_log` | TIME | Horário de encerramento da sessão (`NULL` = crash/desconexão) |
| `dfim_log` | DATE | Data de encerramento (diferente de `data_log` em sessões cross-midnight) |
| `connection_id` | INT | ID de conexão ODBC (uso interno) |

> ⚠️ **Gotcha:** `tini_log` e `tfim_log` são do tipo `TIME` nativo do Sybase. Fazer aritmética direta entre eles **não funciona** para sessões cross-midnight. Use sempre o padrão `YMD(...) + TIME`.

### 7.2 Códigos de Módulo (`sist_log`)

| Código | Módulo |
|---|---|
| `2` | Geral (cadastros, configurações) |
| `5` | **Escrita Fiscal ← ESTE SPEC** |
| `12` | Folha de Pagamento |
| `14` | Contabilidade |

### 7.3 Tabela de Apoio: `bethadba.geempre`

| Coluna | Tipo | Descrição |
|---|---|---|
| `codi_emp` | INT | PK — Código da empresa no Domínio |
| `nome_emp` | VARCHAR | Razão Social completa |
| `cnpj_emp` | VARCHAR | CNPJ da empresa |

### 7.4 Mapeamento de Usuários (Login → Nome Real)

O campo `usua_log` armazena o **login de rede** (formato: `NOME.SOBRENOME` ou apelido simples). Para cruzar com nomes completos:

| Tabela | Campo | Descrição |
|---|---|---|
| `bethadba.auusuarios` | `usuario` | Login de rede (mesmo formato que `usua_log`) |
| `bethadba.usConfUsuario` | `i_usuario` | ID interno do usuário |
| `bethadba.usConfUsuario` | `NOME` | Nome completo do colaborador |
| `bethadba.usConfUsuario` | `SITUACAO` | Status: `1` = Ativo, `0` = Inativo |

> **Nota:** Não há FK direta entre `geloguser.usua_log` e `auusuarios.usuario`. O join deve ser feito via comparação de strings (case-insensitive).

---

## 8. Conectividade ODBC

```python
import pyodbc

# String de conexão padrão
CONN_STR = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'

def conectar_dominio() -> pyodbc.Connection:
    """
    Abre uma conexão ODBC com o banco Domínio (Sybase SQL Anywhere).
    
    Returns:
        Objeto de conexão pyodbc ativo.
    
    Raises:
        pyodbc.Error: Se o DSN não estiver configurado ou a senha for inválida.
    """
    return pyodbc.connect(CONN_STR)
```

> **Requisito:** O DSN `Contabil` precisa estar configurado no ODBC Data Sources do Windows (odbcad32.exe), com o driver SQL Anywhere instalado. Isso é feito pela equipe de TI da DMF.

---

## 9. Gotchas e Armadilhas do Banco Domínio

Esta seção reúne todas as armadilhas e descobertas técnicas mapeadas durante o desenvolvimento. **Leia antes de modificar qualquer query.**

### 9.1 ⚠️ Precisão de Segundos (o mais importante)

**Problema:** `DATEDIFF(minute, ...)` arredonda cada sessão para o minuto inteiro. A soma dos arredondamentos por empresa gera valores divergentes do relatório oficial.

**Solução:** Usar sempre `DATEDIFF(second, ...)` e converter o total de segundos no Python.

```sql
-- ❌ ERRADO — causa divergência
SUM(DATEDIFF(minute, tini_log, tfim_log)) AS minutos

-- ✅ CORRETO — bate com o Domínio
SUM(DATEDIFF(second,
    YMD(YEAR(data_log), MONTH(data_log), DAY(data_log)) + tini_log,
    COALESCE(
        YMD(YEAR(dfim_log), MONTH(dfim_log), DAY(dfim_log)) + tfim_log,
        YMD(YEAR(data_log), MONTH(data_log), DAY(data_log)) + tfim_log
    )
)) AS segundos
```

### 9.2 ⚠️ Campos TIME não suportam subtração direta

No Sybase SQL Anywhere, fazer `DATEDIFF(minute, tini_log, tfim_log)` diretamente em campos `TIME` resulta em valores **negativos** se o trabalho cruzar a meia-noite.

**Solução:** Construir um `DATETIME` completo usando a função `YMD(ano, mes, dia) + TIME`. A adição de uma data com um time no Sybase resulta em um datetime válido para aritmética.

### 9.3 ⚠️ `tfim_log NULL` = Sessão Suja

Quando o sistema Domínio trava ou a máquina do colaborador é reiniciada sem encerrar o sistema, a coluna `tfim_log` fica `NULL`. Essas sessões NÃO devem entrar no cálculo.

**Solução:** Sempre incluir `AND l.tfim_log IS NOT NULL` no WHERE.

### 9.4 ⚠️ Colunas da GELOGUSER — Não Confundir

| Nome ERRADO (não existe) | Nome CORRETO | Descrição |
|---|---|---|
| `thin_log` | `tini_log` | Horário de início |
| `user_id` | `usua_log` | Login de rede do usuário |
| `data_fim` | `dfim_log` | Data de encerramento |

> Esses nomes errados foram tentados durante o desenvolvimento e geraram erro `42S22 - column not found`.

### 9.5 ℹ️ Padrão do `usua_log`

O login armazenado em `usua_log` segue o padrão de login de rede do Windows da DMF:
- **Padrão:** `NOME.SOBRENOME` (ex: `ANALISTA.FISCAL1`, `ANALISTA.FISCAL2`)
- **Exceções:** Usuários antigos ou genéricos não seguem este padrão (ex: `GERENTE.FISCAL`, `COORDENADOR.DP`, `GERENTE`, `ANALISTA.CONTABIL1`)
- **Não é case-sensitive** no Sybase, mas recomendado manter MAIÚSCULO como padrão.

### 9.6 ℹ️ Função YMD no Sybase

A função `YMD(ano, mes, dia)` é nativa do **Sybase SQL Anywhere** e retorna um valor do tipo `DATE`. Ela **não existe** no SQL Server ou PostgreSQL. Se a query for portada para outro banco, substituir por `DATEFROMPARTS(ano, mes, dia)` (SQL Server) ou `MAKE_DATE(ano, mes, dia)` (PostgreSQL).

---

## 10. Scripts e Arquivos do Projeto

| Arquivo | Descrição | Status |
|---|---|---|
| [`extrair_fiscal_direto.py`](./extrair_fiscal_direto.py) | Script principal de extração — query validada com precisão de segundos | ✅ Validado Jan/2026 |
| [`analisar_sessoes_detalhe.py`](./analisar_sessoes_detalhe.py) | Script de debug — extrai sessões individuais por empresa para conferência | ✅ Utilitário |
| [`QUERY_tempo_gasto_fiscal.md`](./QUERY_tempo_gasto_fiscal.md) | Documentação técnica da query SQL com gotchas | ✅ Referência |
| [`processar_horas.py`](./processar_horas.py) | Pipeline principal — integra Folha, Fiscal e Contábil na planilha master | 🔄 Pendente integração Fiscal |
| `CONTROLE_DE_HORAS_DMF.xlsm` | Planilha Master de Controle de Horas (alimentada pelos scripts) | Manual |

---

## 11. Fluxograma do Processo

```
Início do Mês (Extração Fiscal)
           │
           ▼
  ┌─────────────────────────┐
  │  Definir período        │
  │  data_log BETWEEN       │
  │  '01/MM/AAAA' e        │
  │  '31/MM/AAAA'          │
  └───────────┬─────────────┘
              │
              ▼
  ┌─────────────────────────┐
  │  Executar query SQL     │
  │  extrair_fiscal_direto  │
  │  sist_log = 5           │
  │  tfim_log IS NOT NULL   │
  │  DATEDIFF(second)       │
  └───────────┬─────────────┘
              │ resultset: {usua_log, codi_emp, total_segundos}
              ▼
  ┌─────────────────────────┐       ┌─────────────────────────────┐
  │  Agrupar por codi_emp   │──────▶│  Opcional: filtrar por      │
  │  Somar total_segundos   │       │  lista de colaboradores      │
  └───────────┬─────────────┘       └─────────────────────────────┘
              │
              ▼
  ┌─────────────────────────┐
  │  Converter segundos     │
  │  para HH:MM:SS          │
  │  e fração de dia Excel  │
  └───────────┬─────────────┘
              │ dict {codi_emp → fração_dia}
              ▼
  ┌─────────────────────────┐
  │  Abrir planilha Master  │
  │  Aba MM.AAAA            │
  │  Preencher coluna O     │
  │  (match por codi_emp)   │
  └───────────┬─────────────┘
              │
              ▼
  ┌─────────────────────────┐
  │  Atualizar coluna R     │
  │  =O+P+Q por linha       │
  └───────────┬─────────────┘
              │
              ▼
           CONCLUÍDO ✅
```

---

## 12. Problemas Conhecidos e Soluções (Troubleshooting)

Nas execuções operacionais (especialmente consolidadas no ciclo de 03/2026), as armadilhas abaixo corromperam os bancos e exibiram valores bizarros. Conhecê-las evita retrabalho ou pânico em execuções de meses vindouros:

### A. Perda e Corrupção Sumária das Macros VBA no Excel
* **Problema:** Ao utilizar Python (`openpyxl`) para gravar dados na Master `.xlsm`, um esquecimento do parâmetro fez com que o arquivo resultante corrompesse de imediato, e o Excel se recusasse a abrir o arquivo exibindo a mensagem fatal de "arquivo corrompido".
* **Motivo:** O `openpyxl` varre e remove nativamente os binários do VBA/Macros em arquivos por motivos de segurança. Se arquivado sem as macros (que antes existiam), a extensão `.xlsm` entra em conflito.
* **Solução:** **Sempre, sob hipótese inegociável,** o instanciamento no terminal Python requer a sintaxe blindada: `wb = openpyxl.load_workbook(PLANILHA, keep_vba=True)`.

### B. Valores Absurdos de Clientes Ausentes ("Fantasmas")
* **Problema:** Clientes (Ex: 1191 e 1193) listavam pontuações insanas de produtividades na planilha, não possuindo correlação nenhuma com os registros curtos e zerados que as queries do BD retornavam.
* **Motivo:** O script validativo iterava varrendo **apenas os clientes que tivessem horas logadas** no banco de dados. Como esses clientes possuíam ZERO HORAS ativadas pelo Domínio, as chaves não existiam nas matrizes extraídas e os laços do Python simplesmente **pulavam aquela linha no Excel**. O resultado? O LIXO sujo e histórico colado manualmente por alguém de um mês pregresso da contabilidade ficava ali remanescente (e as contagens velhas sujavam o Mês Novo).
* **Regra de Ouro:** Inverter o laço da automação! Deve-se ler iterativamente todas as linhas que a Máster Planner do Mês possui de chaves e preencher ZEROS (`value = 0` = exibido formatado como `00:00:00`) se não retornado registros do Domínio, matando os fantasmas.

### C. Fórmulas Mutantes (Valores Exponenciais quebrando o DateFormat)
* **Problema:** Execução e visualizações morrendo em Loop. Log do OpenPyxl acusando `UserWarning: Cell N459 is marked as a date but the serial value 3.3242749e+18 is outside the limits for dates`.
* **Motivo:** Algum humano arrastou indiscriminadamente formatações interligadas `=N+1*(2+20%)` de baixo para cima nas colunas passadas (Ex: Backfill retroativo na Coluna N). Essa equação exponencial estourou as dezenove casas quadrilhonárias matemáticas, e o mecanismo Visual de formato DateTime Relógio do Excel simplesmente trava com números excedendo o escopo limite de datas no planeta, inviabilizando abrir e compilar as tabelas. 
* **Regra de Ouro:** Não rodar BackFill/Copy-Paste de colunas inteiras de abas velhas sujas e perigosas baseando-se em suas integridades, sem efetuar limpeza ou escanear pureza matemática de "fórmulas embutidas e radioativas" em células antes de salvar a planilha final. A Coluna foi dizimada no script com `cell.value=None` e recuperada.

### D. Conflito Fatal: `keep_vba=True` em arquivos `.xlsx`
* **Problema:** Após a primeira recuperação (salvando a Master como `.xlsx` para contornar a corrupção de macros), os scripts seguintes continuaram usando `keep_vba=True`. Isso injetou metadados binários de VBA dentro de um arquivo que, por definição, não suporta macros. O Excel detecta essa inconsistência e recusa a abertura com erro de "arquivo corrompido".
* **Regra de Ouro Inegociável:**
    * Arquivo **`.xlsm`** → OBRIGATÓRIO `keep_vba=True`
    * Arquivo **`.xlsx`** → PROIBIDO `keep_vba=True`. Usar `keep_vba=False` ou simplesmente omitir o parâmetro.
    * Antes de codificar, **verificar a extensão do arquivo** e condicionar o parâmetro.
* **Código modelo:**
    ```python
    is_xlsm = PLANILHA_MASTER.endswith('.xlsm')
    wb = openpyxl.load_workbook(PLANILHA_MASTER, keep_vba=is_xlsm)
    ```

### E. SUBTOTAL Truncado (Range Não Cobre Todas as Linhas)
* **Problema:** A fórmula `=SUBTOTAL(9,N10:N588)` em N7 estava fixa em 588, mas os dados iam até a linha 777+. Resultado: mais de 500 horas ficaram fora da contabilização, gerando divergência grave no total do mês.
* **Motivo:** Scripts anteriores injetavam o SUBTOTAL com um range hardcoded ou usando `ws.max_row` de uma execução prévia, sem recalcular dinamicamente.
* **Regra de Ouro:** Sempre usar `ws.max_row` no momento exato da gravação para garantir cobertura total:
    ```python
    ws.cell(7, col).value = f'=SUBTOTAL(9,{col_letter}10:{col_letter}{ws.max_row})'
    ```

### F. Backfill com Sobrescrita de Códigos Duplicados
* **Problema:** Ao transferir dados do mês anterior (Backfill), clientes que aparecem em mais de uma linha (ex: Cod 31 – GRUPO GR AGRÍCOLA com 2 linhas, cada uma com valor diferente) tinham ambas as linhas preenchidas com o ÚLTIMO valor, pois o mapeamento usava `dict[cod] = valor` (sobrescrevendo).
* **Motivo:** O dicionário simples `mapa[cod] = valor` perde os valores anteriores quando o mesmo código aparece múltiplas vezes.
* **Regra de Ouro:** O backfill deve mapear como `defaultdict(list)` e casar **linha a linha na ordem de aparição**:
    ```python
    mapa[cod].append(valor)  # preserva ordem
    # Na hora de preencher:
    for i, valor in enumerate(valores_origem):
        if i < len(linhas_destino):
            ws.cell(linhas_destino[i], col).value = valor
    ```

### G. Tipo de Dado: `timedelta` vs `float` na Gravação
* **Problema:** A leitura com `data_only=True` retorna valores como `datetime.timedelta`, e gravar esse objeto diretamente no Excel gera inconsistências na interpretação de fórmulas de SUBTOTAL (o Excel internamente espera frações decimais de dia, não objetos Python).
* **Regra de Ouro:** Sempre converter para float antes de gravar:
    ```python
    if isinstance(valor, timedelta):
        valor = valor.total_seconds() / 86400.0  # fração de dia
    cell.value = valor
    cell.number_format = '[h]:mm:ss'
    ```

---

## Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 2026-03-11 | Criação do spec. Validação com precisão de segundos em Jan/2026. |
| 1.1 | 2026-03-11 | Adicionada regra de negócio do adicional de 70% (fator 1.70) sobre o tempo bruto antes de gravar na coluna O. |
| 1.2 | 2026-04-12 | Modificado o adicional para 80% (fator 1.80) conforme instrução atualizada. |
| 1.3 | 2026-04-13 | Adicionados itens D-G no Troubleshooting: conflito keep_vba/xlsx, SUBTOTAL truncado, backfill duplicados, timedelta vs float. |
