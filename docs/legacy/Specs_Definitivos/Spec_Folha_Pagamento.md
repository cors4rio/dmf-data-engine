# Spec: Cálculo de Folha de Pagamento (Setor Pessoal / DP)
> **Projeto:** N8N Automação — DMF Contabilidade
> **Versão:** 1.2
> **Última atualização:** 2026-03-11
> **Responsável técnico:** Ícaro Conceição
> **Validado em:** Janeiro/2026 — empresas 8001 (Adriana) e 856 (Agromix) confirmaram a lógica de cruzamento.

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Fontes de Dados](#2-fontes-de-dados)
   - 2.1 [Banco de Dados Domínio (Sybase/ODBC)](#21-banco-de-dados-domínio-sybasedbc)
   - 2.2 [Planilha de Controle de Empregados](#22-planilha-de-controle-de-empregados)
   - 2.3 [Arquivo de Exceções — DP NÃO](#23-arquivo-de-exceções--dp-não)
3. [Pipeline de Processamento](#3-pipeline-de-processamento)
4. [Fórmula de Cálculo de Horas](#4-fórmula-de-cálculo-de-horas)
5. [Regras de Exceção](#5-regras-de-exceção)
6. [Estrutura da Planilha Master (CONTROLE_DE_HORAS_DMF)](#6-estrutura-da-planilha-master)
7. [Queries SQL no Banco Domínio](#7-queries-sql-no-banco-domínio)
22. [Tabelas e Campos Chave — Módulo Folha (Domínio)](#8-tabelas-e-campos-chave--módulo-folha-domínio)
23. [Conectividade ODBC](#9-conectividade-odbc)
24. [Scripts e Arquivos do Projeto](#10-scripts-e-arquivos-do-projeto)
25. [Boas Práticas e Regras de Negócio](#11-boas-práticas-e-regras-de-negócio)
26. [Fluxograma do Processo](#12-fluxograma-do-processo)
27. [Problemas Conhecidos e Soluções (Troubleshooting)](#13-problemas-conhecidos-e-soluções-troubleshooting)

---

## 1. Visão Geral

O **cálculo da Folha de Pagamento (Setor Pessoal / DP)** representa o tempo estimado que a equipe da DMF gasta processando a folha de cada cliente. Esse dado alimenta a **Planilha Mestre de Controle de Horas** (`CONTROLE_DE_HORAS_DMF.xls`), que consolida o tempo total por cliente dividido em três setores:

| Coluna Excel | Setor | Fonte |
|---|---|---|
| O — Horário Fiscal | Escrita Fiscal | Relatório Gestta (`.xls`) |
| P — Horário Contábil | Contabilidade | Planilha HORAS CONTABEIS (.xlsx) |
| Q — Horário Pessoal | **Folha de Pagamento (DP)** | **Planilha Controle de Empregados + Domínio** |
| R — Total | Soma O+P+Q | Fórmula Excel `=O+P+Q` |

> **Importante:** O tempo de Folha (coluna Q) é calculado com base **na quantidade de empregados ativos** de cada empresa naquele mês, somando **Funcionários + Estagiários + Contribuintes**. Empresas que não fazem DP na DMF ou que utilizam sistema próprio são excluídas ou substituídas pelo código `DP NÃO`.

> **Mínimo:** Empresas que fazem DP mas têm **zero empregados ativos** no mês recebem **00:05:00** (5 minutos), nunca zero.

---

## 2. Fontes de Dados

### 2.1 Banco de Dados Domínio (Sybase/ODBC) ⭐ Fonte Primária

O sistema ERP **Domínio Sistemas** (da Benner) armazena os dados oficiais de todos os clientes. A conexão é feita via **ODBC** com o driver **SQL Anywhere**.

#### Parâmetros de Conexão

| Parâmetro | Valor |
|---|---|
| **Protocolo** | ODBC (Driver SQL Anywhere) |
| **DSN Padrão** | `Contabil` |
| **Usuário** | `EXTERNO` |
| **Schema** | `bethadba` |

> ⚠️ **Segurança:** A senha não deve ser exposta em logs ou código versionado. Utilizá-la apenas via variáveis de ambiente ou arquivo `.env` não versionado.

#### Tabelas do Módulo Folha de Pagamento

| Tabela Domínio | Finalidade |
|---|---|
| `bethadba.foempregados` | Dados dos empregados — campo `vinculo` define o tipo |
| `bethadba.foparmto` | Parâmetros de cálculo da folha (configurações por empresa) |

#### Mapeamento de Tipos via Campo `vinculo`

| `vinculo` | Tipo de Empregado | Qtd. total no banco |
|---|---|---|
| `1` | **Funcionário** (CLT) | ~35.900 |
| `6` | **Estagiário** | ~125 |
| `11` | **Contribuinte Individual** | ~1.800 |

> Todos os três tipos **somam para a fórmula**. O campo usado é `vinculo IN (1, 6, 11)`.

#### Tabelas de Apoio (Cadastros e Vigências)

| Tabela Domínio | Finalidade |
|---|---|
| `bethadba.geempre` | Cadastro mestre de empresas (`codi_emp`, `nome_emp`, `cnpj_emp`) |
| `bethadba.efparametro_vigencia` | Regime tributário vigente por empresa e período |
| `bethadba.ctlancto` | Lançamentos contábeis (auditoria cruzada) |
| `bethadba.efsaidas` | Faturamento de vendas/produtos (`dsai_sai`, `vcon_sai`) |
| `bethadba.efservicos` | Faturamento de serviços (`dser_ser`, `vcon_ser`) |

---

### 2.2 Planilha de Controle de Empregados ⚠️ Fallback/Validação

> **A planilha Carol é usada apenas como fallback** quando os dados extraídos do Domínio não batem com a realidade do mês. A fonte primária é sempre o banco Domínio.

**Arquivo:** `Controle de Empregados MM(CAROL).xls`
**Produzido por:** Responsável do DP (Carol) mensalmente.
**Formato:** `.xls` (Excel legado, lido via biblioteca `xlrd`)

#### Estrutura da planilha

| Linha | Conteúdo |
|---|---|
| 0 (Header 1) | Cabeçalhos principais das colunas (ex: categorias de empregados) |
| 1 (Header 2) | Sub-cabeçalhos ou complementos |
| 2+ (Dados) | Uma linha por empresa |

#### Colunas lidas por código (0-indexed)

| Índice Col. | Campo |
|---|---|
| 0 | Código da empresa no Domínio (`codi_emp`) |
| 1 | Nome/Razão Social da empresa |
| 7, 9, 11, 13, 15, 17, 19, 21, 23 | Quantidade de empregados ativos por categoria |

> **Regra:** As colunas ímpares (7, 9, 11...) representam categorias distintas de empregados (ex: CLT, PJ, Sócios, etc). A soma de todas as categorias resulta na `soma_ativos`.

---

### 2.3 Arquivo de Exceções — DP NÃO

**Arquivo:** `nao_faz_setor/DP NAO.txt`
**Finalidade:** Lista manual de empresas que **não fazem Folha de Pagamento na DMF** ou que usam sistema próprio.

#### Formatos de linha aceitos pelo parser

| Formato | Exemplo | Ação |
|---|---|---|
| Apenas nome (sem código) | `AGRO EMPRESA FANTASIA LTDA` | Marcado como `DP NÃO` via nome |
| `CÓDIGO\tNOME` | `988\tLE BRUT INDUSTRIA...` | Marcado como `DP NÃO` via código |
| `CÓDIGO;NOME` | `853;PET SHOP FANTASIA LTDA` | Marcado como `DP NÃO` via código |
| `CÓDIGO NOME (FAZ CONSULTORIA, LANCAR APENAS 1:30 HORA)` | `1107 GLOBAL MANUTENCOES...` | Registra `1:30` h como consultoria |
| `993\tNOME (FAZ CONSULTORIA, LANCAR APENAS 1:30)` | `993\tLE BRUT...` | Registra `1:30` h como consultoria |
| `Não entra - sistema próprio\tNOME` | Linha sem código | Ignorado (sistema próprio) |

> As empresas de consultoria (flag `1:30`) recebem **exatamente 1h30** na coluna Q em vez de zero.

---

## 3. Pipeline de Processamento

O processamento segue este fluxo, implementado em **`processar_horas.py`**:

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE DE FOLHA (DP)                   │
└─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │  1. Query Banco Domínio (ODBC) — VALIDADA      │
  │    foempregados LEFT JOIN forescisoes          │
  │    vinculo IN (1, 6, 11)                       │
  │    por empresa (codi_emp)                      │
  │    Ref: QUERY_folha_empregados.md              │
  └──────────────┬──────────────────────────────────┘
                 │   total_para_formula por empresa
                 ▼
  ┌──────────────────────┐   ← FALLBACK: se Domínio discrepante
  │  1b. Ler Planilha DP │      usar Carol para conferência manual
  │  (Carol, xlrd)       │      Colunas [7,9,11,13,15,17,19,21,23]
  └──────────┬───────────┘
             │   soma_ativos por empresa
             ▼
  ┌──────────────────────────────────────────┐
  │ 2. Aplicar Fórmula de Horas              │
  │    se total > 0: (total × 0,33) + 1,5   │
  │    se total = 0: 5 minutos (00:05:00)    │  ← mínimo obrigatório
  └──────────┬───────────────────────────────┘
             │   dict_folha {codi_emp → horas, nome → horas}
             ▼
  ┌──────────────────────┐
  │ 3. Ler Exceções      │ ← DP NAO.txt
  │    DP NÃO            │   Identifica: dp_nao_codes e consultoria_codes
  └──────────┬───────────┘
             │   override de valores
             ▼
  ┌──────────────────────┐
  │ 4. Preencher Planilha│ ← CONTROLE_DE_HORAS_DMF.xls (Aba MM.AAAA)
  │    Master (coluna Q) │   Match por: codi_emp (col H) ou nome (cols I/K)
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ 5. Atualizar Total   │   Fórmula Excel: =O{row}+P{row}+Q{row}
  │    (coluna R)        │   Formato: [h]:mm:ss
  └──────────────────────┘
```

---

## 4. Fórmula de Cálculo de Horas

### Fórmula Principal

```
total = Funcionários (vinculo=1) + Estagiários (vinculo=6) + Contribuintes (vinculo=11)

se total > 0:
    horas_dp = (total × 0,33) + 1,5
se total = 0:
    horas_dp = 5/60  →  exibir como 00:05:00  (mínimo obrigatório)
```

**Onde:**
- `total` = soma de Funcionários + Estagiários + Contribuintes ativos no mês, extraídos do Domínio via `vinculo IN (1, 6, 11)`
- `0,33` = fator de proporcionalidade (~20 min por empregado)
- `1,5` = overhead fixo de 1h30 (abertura, fechamento, envio eSocial)
- **Mínimo:** `00:05:00` quando total = 0 (empresa tem DP mas sem empregados no mês)

**Exemplos práticos:**

| Qtd. Total (F+E+C) | Cálculo | Resultado |
|---|---|---|
| **0** | mínimo obrigatório | **`00:05:00`** |
| 1 | (1 × 0,33) + 1,5 | `1,83 h` |
| 5 | (5 × 0,33) + 1,5 | `3,15 h` |
| 10 | (10 × 0,33) + 1,5 | `4,80 h` |
| 20 | (20 × 0,33) + 1,5 | `8,10 h` |
| 50 | (50 × 0,33) + 1,5 | `18,00 h` |

### Conversão para Formato Excel

O valor de horas (float) é dividido por **24** antes de ser inserido no Excel:

```python
# Constante de mínimo (5 minutos como fração de dia para o Excel)
MINIMO_5_MIN = (5 / 60) / 24.0  # → exibe 00:05:00 no formato [h]:mm:ss

# Lógica de cálculo
if total_para_formula > 0:
    horas = (total_para_formula * 0.33) + 1.5
    sh_m.cell(row=row, column=17, value=horas / 24.0)
else:
    sh_m.cell(row=row, column=17, value=MINIMO_5_MIN)
```

Isso ocorre porque o Excel armazena tempo internamente como fração do dia. Com o formato de célula `[h]:mm:ss`, o valor é exibido corretamente.

### Fórmula de Total (Coluna R)

```excel
=O{row}+P{row}+Q{row}
```
**Formato da célula:** `[h]:mm:ss`
Implementado em `atualizar_total_com_dp.py`.

---

## 5. Regras de Exceção

### 5.1 Empresa com DP NÃO

Empresas listadas em `DP NAO.txt` sem flag de consultoria:
- A coluna Q recebe o valor **literal** `"DP NÃO"` (string, não numérico)
- Na coluna D da aba da planilha master, também pode aparecer `"DP NÃO"` como flag extra

### 5.2 Empresa com Consultoria (1:30)

Empresas com flag `FAZ CONSULTORIA, LANCAR APENAS 1:30`:
- A coluna Q recebe o valor **`"1:30"`** (string)
- Isso representa 1 hora e 30 minutos de trabalho de consultoria de DP

**Empresas com consultoria identificadas no arquivo (exemplos):**
- `1107 — CONSTRUTORA FANTASIA LTDA`
- `993 — INDUSTRIA DE ROUPAS FANTASIA LTDA`
- `837 — PET SHOP FANTASIA LTDA`

### 5.3 Empresa com Sistema Próprio

Empresas com tag `"Não entra - sistema próprio"`:
- Ignoradas pelo processamento (sem código DOM identificável facilmente)
- Não recebem valor na coluna Q

### 5.4 Prioridade das Regras (Cascata)

```
1º → Código no dict consultoria_codes? → Lança "1:30"
2º → Código no set dp_nao_codes?       → Lança "DP NÃO"
3º → Coluna D da planilha = "DP NÃO"? → Lança "DP NÃO" (fallback por nome)
4º → Nenhuma exceção?                  → Usa valor calculado pela fórmula
```

---

## 6. Estrutura da Planilha Master

**Arquivo:** `CONTROLE_DE_HORAS_DMF.xls`
**Aba:** `MM.AAAA` (ex: `12.2025`)
**Dados começam na linha 10** (linhas 1-9 são cabeçalhos e configurações)

### Mapeamento de Colunas (openpyxl, 1-indexed)

| Nº Col. | Letra Excel | Nome do Campo | Tipo |
|---|---|---|---|
| 4 | D | Flag DP (ex: "DP NÃO") | Texto |
| 8 | H | **Código Domínio** (`codi_emp`) | Numérico |
| 9 | I | Nome Fantasia | Texto |
| 11 | K | Razão Social | Texto |
| 14 | N | Tempo Domínio Fiscal (bruto) | Fração de dia |
| 15 | O | **Horário Fiscal** (bruto × 1.65 = +65% corte) | Fração de dia |
| 16 | P | **Horário Contábil** | Fração de dia |
| 17 | Q | **Horário Pessoal (Folha DP)** | Fração de dia ou texto |
| 18 | R | **Total** (`=O+P+Q`) | Fração de dia |

### Lógica de Match para Preenchimento

```python
# Ordem de precedência para matching (processar_horas.py, linha 207-222):
v_folha = dict_folha.get(c_str)        # 1º: Código Domínio (mais confiável)
       or dict_folha.get(n_limpo)       # 2º: Razão Social (uppercase, sem espaços)
       or dict_folha.get(nf_limpo)      # 3º: Nome Fantasia (fallback final)
```

---

## 7. Queries SQL no Banco Domínio

### 7.1 — Empregados Ativos com Breakdown por Tipo (QUERY PRINCIPAL — VALIDADA)

> **Tabelas:** `bethadba.foempregados` + `bethadba.forescisoes`
> **Finalidade:** Conta Funcionários, Estagiários e Contribuintes ATIVOS por empresa num mês específico.
> **Validada em:** Janeiro/2026 — resultado bateu exatamente com a realidade (8001=11, 856=6).
> **Referência completa:** [`QUERY_folha_empregados.md`](./QUERY_folha_empregados.md)

```sql
SELECT
    e.codi_emp                                                        AS Codigo_Cliente,
    SUM(CASE WHEN e.vinculo = 1  THEN 1 ELSE 0 END)                  AS Qtd_Funcionarios,
    SUM(CASE WHEN e.vinculo = 6  THEN 1 ELSE 0 END)                  AS Qtd_Estagiarios,
    SUM(CASE WHEN e.vinculo = 11 THEN 1 ELSE 0 END)                  AS Qtd_Contribuintes,
    SUM(CASE WHEN e.vinculo IN (1, 6, 11) THEN 1 ELSE 0 END)         AS Total_Para_Formula
FROM bethadba.foempregados e
-- Exclui quem foi demitido ANTES do início do mês (forescisoes.demissao)
LEFT JOIN bethadba.forescisoes r
    ON r.codi_emp     = e.codi_emp
   AND r.i_empregados = e.i_empregados
   AND r.demissao     < '{{DATA_INICIO_MES}}'
WHERE e.admissao <= '{{DATA_FIM_MES}}'  -- Admitido até o fim do mês
  AND r.i_empregados IS NULL            -- Sem rescisão antes do início do mês
GROUP BY e.codi_emp
ORDER BY e.codi_emp;
```

**Parâmetros N8N:**
- `{{DATA_INICIO_MES}}` → ex: `2026-01-01`
- `{{DATA_FIM_MES}}` → ex: `2026-01-31`

**Lógica da query (validada em Jan/2026):**
- `e.admissao <= fim_do_mes` → admitido antes ou durante o mês
- `LEFT JOIN forescisoes` → verifica se há rescisão registrada
- `r.demissao < DATA_INICIO_MES` → excluído se demissão foi **antes** do mês começar
- `r.i_empregados IS NULL` → inclui somente quem **não** tem rescisão anterior ao mês

> ⚠️ **IMPORTANTE:** A tabela `foempregados` contém histórico completo — ex-funcionários dos anos anteriores.
> Sem o JOIN com `forescisoes`, o banco retorna muito mais registros que os reais.
> **Este JOIN é obrigatório para precisão.**

---

### 7.2 — Regime Tributário Vigente

> **Tabela:** `bethadba.efparametro_vigencia`
> **Finalidade:** Identifica o enquadramento fiscal oficial de cada empresa no período.

```sql
SELECT
    p.codi_emp AS Codigo_Cliente,
    CASE p.rfed_par
        WHEN 1 THEN 'Lucro Real'
        WHEN 2 THEN 'Simples Nacional'
        WHEN 4 THEN 'Simples Nacional'
        WHEN 5 THEN 'Lucro Presumido'
        WHEN 7 THEN 'Lucro Arbitrado'
        WHEN 8 THEN 'Imune / Isenta'
        ELSE 'Outros'
    END AS Regime_Vigente
FROM
    bethadba.efparametro_vigencia p
INNER JOIN (
    SELECT codi_emp, MAX(vigencia_par) AS max_vigencia
    FROM bethadba.efparametro_vigencia
    WHERE vigencia_par <= '{{DATA_FIM_MES}}'
    GROUP BY codi_emp
) ult ON p.codi_emp = ult.codi_emp
      AND p.vigencia_par = ult.max_vigencia;
```

**Regra de Ouro:** Sempre usar `MAX(vigencia_par) <= DATA_FIM_MES` para capturar o regime **vigente** no período, evitando pegar registros futuros ou duplicados.

---

### 7.3 — Consulta de Cadastro Mestre das Empresas

> **Tabela:** `bethadba.geempre`

```sql
SELECT
    codi_emp,
    nome_emp AS Razao_Social,
    cnpj_emp AS CNPJ
FROM
    bethadba.geempre
ORDER BY
    codi_emp;
```

---

## 8. Tabelas e Campos Chave — Módulo Folha (Domínio)

### `bethadba.foempregados` — Empregados (Histórico Completo)

| Campo | Descrição | Uso na Query |
|---|---|---|
| `codi_emp` | Código da empresa (FK para `geempre`) | JOIN, GROUP BY |
| `i_empregados` | Código interno único do empregado | JOIN com `forescisoes` |
| `admissao` | Data de admissão do empregado | Filtro `<= DATA_FIM_MES` |
| `vinculo` | Tipo de vínculo (1=CLT, 6=Estag, 11=Contrib) | CASE WHEN / SUM |

> ⚠️ Esta tabela acumula **histórico completo** — não exclui ex-funcionários automaticamente.
> Sempre cruzar com `forescisoes` para obter apenas os ativos do mês.

### `bethadba.forescisoes` — Rescisões / Demissões

| Campo | Descrição | Uso na Query |
|---|---|---|
| `codi_emp` | Código da empresa | JOIN com `foempregados` |
| `i_empregados` | Código interno do empregado rescindido | JOIN com `foempregados` |
| `demissao` | Data da rescisão/demissão | Filtro `< DATA_INICIO_MES` no LEFT JOIN |

> ✅ **Regra validada:** `LEFT JOIN forescisoes ON ... AND demissao < DATA_INICIO_MES` + `WHERE r.i_empregados IS NULL`
> Retorna apenas quem **não** tem rescisão antes do mês — ou seja, ativos reais na competência.

### `bethadba.foparmto` — Parâmetros de Cálculo

| Campo | Descrição |
|---|---|
| `codi_emp` | Código da empresa |
| (demais campos) | Parâmetros internos de cálculo da folha (alíquotas, bases, etc.) |

> ⚠️ Esta tabela ainda não foi completamente mapeada. Uso futuro para automação de cálculo interno.

### `bethadba.geempre` — Cadastro de Empresas

| Campo | Descrição |
|---|---|
| `codi_emp` | **Chave Única** — Código da empresa no Domínio |
| `nome_emp` | Razão Social |
| `cnpj_emp` | CNPJ (formato sem pontuação) |

---

## 9. Conectividade ODBC

A conexão com o banco Domínio é feita usando `pyodbc` em Python:

```python
import pyodbc

conn = pyodbc.connect(
    'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<senha_do_env>'
)
cursor = conn.cursor()

cursor.execute("""
    SELECT codi_emp, COUNT(*) AS Qtd_Empregados_Ativos
    FROM bethadba.foempregados
    WHERE admissao <= '2025-12-31'
    AND (demissao IS NULL OR demissao >= '2025-12-01')
    GROUP BY codi_emp
""")

rows = cursor.fetchall()
```

**Tratamento obrigatório de `None`:** O Sybase retorna campos vazios como `None` em Python. Sempre converter antes de usar:

```python
# Tratamento seguro de código de empresa
cod_str = str(int(float(str(cod_raw).strip().split('.')[0])))

# Tratamento seguro de None em nomes
nome = str(nome_raw).strip().upper() if nome_raw else ""
```

---

## 10. Scripts e Arquivos do Projeto

| Arquivo | Linguagem | Função |
|---|---|---|
| `processar_horas.py` | Python | **Script principal** — Lê as 3 fontes (Folha, Fiscal, Contábil) e preenche o Master |
| `test_folha.py` | Python | Teste isolado da leitura da planilha de empregados e cálculo de horas |
| `search_folha_fat.py` | Python | Utilitário para buscar tabelas de Folha e Faturamento no JSON de schema do Domínio |
| `limpar_dp_e_minimo.py` | Python | Aplica as exceções do `DP NAO.txt` na coluna Q da planilha Master |
| `atualizar_total_com_dp.py` | Python | Recalcula e insere a fórmula `=O+P+Q` na coluna R (Total) |
| `nao_faz_setor/DP NAO.txt` | Texto | Lista manual de empresas que não fazem DP na DMF |
| `QUERY_folha_empregados.md` | Markdown | **Queries SQL validadas** para extração de Funcionários/Estagiários/Contribuintes do Domínio |
| `validacao_quantidade_estagiarios_mes01.md` | Markdown | Query de validação de estagiários (mês 01/2026) |
| `Controle de Empregados MM(CAROL).xls` | Excel (.xls) | **Fallback/validação** — usado quando dados do Domínio não batem com a realidade |
| `CONTROLE_DE_HORAS_DMF.xls` | Excel (.xls) | Planilha mestre — destino de todos os dados calculados |
| `dominio_columns.json` | JSON | Schema completo de colunas de todas as tabelas do Domínio |
| `dominio_tables.json` | JSON | Lista de todas as tabelas do banco Domínio |
| `dominio_relationships.json` | JSON | Relacionamentos entre tabelas (FKs mapeadas) |
| `PADRAO_INTEGRACAO_DOMINIO.md` | Markdown | Guia mestre de integração ODBC com o Domínio |
| `Mapeamento_Dominio_Contabil.md` | Markdown | Mapeamento técnico das tabelas e regras do módulo Contábil |
| `N8N_Queries_Planilha_Contabil.md` | Markdown | Queries SQL validadas para uso no N8N |

---

## 11. Boas Práticas e Regras de Negócio

### Regras de Ouro

1. **Vigência Temporal:** Para buscar o dado ATUAL no Domínio, sempre usar sub-query de `MAX(vigencia)`:
   ```sql
   WHERE vigencia = (SELECT MAX(vigencia) FROM tabela WHERE codi_emp = p.codi_emp AND vigencia <= 'DATA_AFETADA')
   ```

2. **Código > Nome:** O `codi_emp` é a chave mais confiável. Usar o nome da empresa apenas como fallback (pode ter variações de escrita).

3. **Evitar `descricao_par`:** O campo de descrição é de livre digitação no Domínio e pode conter textos incorretos ou imprecisos. Usar sempre o **código** (`rfed_par`, `forma_tributacao`).

4. **`data_only=True` no Excel:** Ao abrir planilhas `.xlsx` com `openpyxl`, sempre usar `data_only=True` para ler valores calculados (não as fórmulas):
   ```python
   wb = openpyxl.load_workbook(arquivo, data_only=True)
   ```

5. **None do Sybase:** Sempre tratar campos `None` antes de processar. O Sybase retorna `None` para campos vazios.

6. **CNPJs como String:** Normalizar CNPJ removendo pontuação antes de comparar:
   ```python
   cnpj = re.sub(r'\D', '', str(cnpj_raw))
   ```

7. **Índice duplo no dict_folha:** O dicionário de folha indexa por **código** E por **nome** (uppercase) para permitir dois tipos de match:
   ```python
   dict_folha[cod_str] = horas
   dict_folha[nome_limpo] = horas  # fallback para match por nome
   ```

### Regras de Negócio

- Empresa com `total_para_formula = 0` recebe **00:05:00** (5 minutos mínimos) — nunca zero.
- O mínimo de horas para empresa com pelo menos 1 empregado ativo é sempre **1,5h** (overhead fixo).
- Empresas de consultoria de DP recebem exatamente **1,5h** (marcadas como `"1:30"` no arquivo de exceções).
- O arquivo `DP NAO.txt` deve ser mantido atualizado manualmente pela equipe do DP.
- **Fonte primária sempre é o Domínio.** A planilha Carol (`Controle de Empregados`) é fallback para validar discrepâncias.

---

## 12. Fluxograma do Processo

```
                        ┌─────────────────────┐
                        │   INÍCIO DO MÊS     │
                        │   (Ex: 12/2025)     │
                        └──────────┬──────────┘
                                   │
              ┌────────────────────▼──────────────────────────┐
              │  1. QUERY DOMÍNIO (Fonte Primária)             │
              │  bethadba.foempregados                         │
              │  vinculo IN (1=Func, 6=Estag, 11=Contrib)     │
              │  → Total_Para_Formula por empresa              │
              └────────────────────┬──────────────────────────┘
                                   │
              ┌────────────────────▼──────────────────────────┐
              │  1b. [FALLBACK] Planilha Carol                 │
              │  Controle de Empregados MM.xls                │
              │  Usado apenas se dados Domínio discrepantes   │
              └────────────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  2. Aplicar Fórmula                  │
                    │  total > 0: (total × 0,33) + 1,5    │
                    │  total = 0: 00:05:00 (mínimo)        │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  3. Exceções DP NAO.txt      │
                    │  → dp_nao_codes → "DP NÃO"  │
                    │  → consultoria → "1:30"      │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  4. Preenche Planilha Master  │
                    │  CONTROLE_DE_HORAS_DMF.xls   │
                    │  Aba MM.AAAA / Coluna Q      │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  5. Coluna R = =O+P+Q        │
                    │  Formato: [h]:mm:ss          │
                    └──────────────┬───────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ PLANILHA FINALIZADA  │
                        │ TOTAL = O + P + Q    │
                        └─────────────────────┘
```

---

## 13. Problemas Conhecidos e Soluções (Troubleshooting)

Ao longo das execuções e do desenvolvimento da arquitetura, os seguintes problemas podem se manifestar e **já possuem soluções blindadas** aplicadas no processo atual:

### A. Erro de ODBC e Driver Architecture `(IM014)`
* **Problema:** Ao instanciar a automação, falhas entre o driver 32-bits e a arquitetura 64-bits causam exclusão e quebra de leitura do DB SQL do Domínio.
* **Solução (Anti-bloqueio):** Caso a conexão DB apresente instabilidade, o contorno documentado é a migração exclusiva pro *fallback* nativo: Processamento imediato pelo arquivo Excel de *"Controle de Empregados (CAROL).xls"*, lendo as colunas de quantidade 7, 9 e 11 diretamente. Somar (func + estag + contrib).

### B. Mapeamento de Clientes Ignorados (Valores Quebrados no Excel)
* **Problema:** A leitura bruta no OpenPyxl identificava células formatadas contendo números em ponto flutuante oculto no raw text (Ex: `1152.0`) na Coluna H. Ao rodar `isdigit()`, a restrição do Python pulava o cliente, listando dezenas de clientes legítimos como "Órfãos/Ignorados".
* **Regra Ouro:** Todo valor de código na Planilha Master deve ser mapeado fazendo casting duplo para contornar qualquer customização manual da planilha: `int(float(str(codigo).strip()))`.

### C. Visualização Falsa (Horas "Totalmente Diferentes" pós 24 horas)
* **Problema:** Acima de 24 horas estimadas de trabalho no DP (`1 Dia = 24 / 24h` = Valor decimal do Excel > 1.0), o Excel esconde as primeiras 24 horas devido à formatação comum de `h:mm`, apresentando por exemplo `01:15` quando o conteúdo contido estritamente tem `25:15:36`.
* **Regra Ouro:** Forçar através do OpenPyxl a injeção da formatação `c.number_format = '[h]:mm:ss'` sempre que escrever valores decimais de tempo na planilha Master. Isso isola falhas de edição anterior do usuário.

### D. Dados Duplicados na Planilha Master (Mapeamento Dicionário)
* **Problema:** Clientes reincidentes (em mais de uma linha na Master) podem ter seu primeiro bloco "Zerado" ("Vazio") pois instâncias comuns de dicionário (`d[cod] = row`) sobrescrevem os IDs iguais, atualizando apenas a última linha mapeada para aquele cliente (Ex.: RIGEL, de cód. 1480).
* **Regra Ouro:** Ao criar o mapeamento, o Dict deve apontar para uma lista de linhas `d[cod].append(row)`. No momento do preenchimento e log `for`, é executado um loop preenchendo todos os `row_ws` contidos nele sem omissões.

### E. SUBTOTAL() Estourado ou Quebrado (Invisível) em Q7
* **Problema 1:** A string da fórmula de `Q7` costuma congelar em sua expansão pregressa (ex. `Q10:Q739`). Quando novas empresas eram cadastradas na linha 800+, essas horas sequer contabilizavam o quadro.
* **Problema 2:** Exceções inseridas como String (ex: `1:30`) para consultorias impediam a contabilidade do SUBTOTAL que lê numéricos.
* **Solução / Regra Ouro:** O script autocalcula e reinjeta `f"=SUBTOTAL(9,Q10:Q{ws.max_row})"`. Regras de "Valor estático e não calculados (Consultorias)", embora pareçam visuais `1:30`, devem **sempre ser passadas em float (`1.5 / 24.0`)** pelo Python para garantir processamento de equações da Master Spreadsheet.

---

## Referências e Arquivos Relacionados

- [`PADRAO_INTEGRACAO_DOMINIO.md`](./PADRAO_INTEGRACAO_DOMINIO.md) — Guia mestre de conexão e integração com Domínio
- [`Mapeamento_Dominio_Contabil.md`](./Mapeamento_Dominio_Contabil.md) — Tabelas e campos do módulo Contábil
- [`N8N_Queries_Planilha_Contabil.md`](./N8N_Queries_Planilha_Contabil.md) — Queries SQL validadas para N8N
- [`processar_horas.py`](./processar_horas.py) — Script principal de processamento
- [`limpar_dp_e_minimo.py`](./limpar_dp_e_minimo.py) — Aplicação de exceções DP NÃO
- [`atualizar_total_com_dp.py`](./atualizar_total_com_dp.py) — Recálculo da coluna Total
- [`nao_faz_setor/DP NAO.txt`](./nao_faz_setor/DP%20NAO.txt) — Lista de exceções do DP

---

*Documento gerado com base na análise dos arquivos existentes no projeto. Reflections a implementação real validada — não teórica.*
