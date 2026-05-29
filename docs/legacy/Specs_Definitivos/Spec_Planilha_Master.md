# Spec: Planilha Master de Controle de Horas (CONTROLE_DE_HORAS_DMF)
> **Projeto:** N8N Automação — DMF Contabilidade
> **Versão:** 1.0
> **Última atualização:** 2026-03-11
> **Responsável técnico:** Ícaro Conceição
> **Arquivo físico:** `CONTROLE_DE_HORAS_DMF.xlsm`

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Estrutura e Mapeamento de Colunas](#2-estrutura-e-mapeamento-de-colunas)
3. [Identificação de Clientes — Lookup Duplo](#3-identificação-de-clientes--lookup-duplo)
   - 3.1 [Valores Especiais no Campo Código Domínio (Coluna H)](#31-valores-especiais-no-campo-código-domínio-coluna-h)
4. [Regras de Alimentação por Coluna](#4-regras-de-alimentação-por-coluna)
   - 4.1 [Coluna N — Mês Anterior Fiscal](#41-coluna-n--mês-anterior-fiscal)
   - 4.2 [Coluna O — Horário Fiscal](#42-coluna-o--horário-fiscal)
   - 4.3 [Coluna P — Horário Contábil](#43-coluna-p--horário-contábil)
   - 4.4 [Coluna Q — Horário Pessoal (DP)](#44-coluna-q--horário-pessoal-dp)
   - 4.5 [Coluna R — Total](#45-coluna-r--total)
5. [Sistemas de Exceção](#5-sistemas-de-exceção)
   - 5.1 [DP NÃO — Empresas sem Folha de Pagamento na DMF](#51-dp-não--empresas-sem-folha-de-pagamento-na-dmf)
   - 5.2 [NÃO FAZ CONTÁBIL — Empresas sem Contabilidade na DMF](#52-não-faz-contábil--empresas-sem-contabilidade-na-dmf)
6. [Pipeline Geral de Preenchimento](#6-pipeline-geral-de-preenchimento)
7. [Regras de Ouro (O que NÃO fazer)](#7-regras-de-ouro-o-que-não-fazer)
8. [Relação com os outros Specs](#8-relação-com-os-outros-specs)
9. [Scripts e Arquivos do Projeto](#9-scripts-e-arquivos-do-projeto)

---

## 1. Visão Geral

A **Planilha Master** (`CONTROLE_DE_HORAS_DMF.xlsm`) é o **produto final consolidado** do processo de automação. Ela reúne, em uma única aba por mês, o tempo total de trabalho da equipe DMF por cliente, distribuído em três setores:

| Setor | Coluna | Fonte | Spec |
|---|---|---|---|
| Escrita Fiscal | O | Banco Domínio (`GELOGUSER`) + adicional 80% | [Spec_Produtividade_Fiscal.md](./Spec_Produtividade_Fiscal.md) |
| Contabilidade | P | Planilha HORAS CONTABEIS (.xlsx) | — |
| Pessoal / DP | Q | Domínio (`foempregados`) + fórmula | [Spec_Folha_Pagamento.md](./Spec_Folha_Pagamento.md) |
| **Total** | **R** | **=O+P+Q** | **—** |

> **Importante:** A planilha nunca deve ser preenchida manualmente durante o processo de automação. Todas as escritas são feitas via scripts Python com `openpyxl`. Edições manuais devem ser feitas apenas para correções pontuais e documentadas.

---

## 2. Estrutura e Mapeamento de Colunas

**Aba de trabalho:** `MM.AAAA` (ex: `01.2026`, `02.2026`)
**Dados começam na linha 10** (linhas 1-9 são cabeçalhos e configurações)

### Mapeamento completo (openpyxl, 1-indexed)

| Nº Col. | Letra | Nome do Campo | Tipo | Quem preenche |
|---|---|---|---|---|
| 4 | D | Flag de exceção (ex: `"DP NÃO"`) | Texto | Script (exceções) |
| 8 | H | **Código Domínio** (`codi_emp`) | Numérico ou texto especial | Planilha (manual/importação) |
| 9 | I | Nome Fantasia | Texto | Planilha (manual/importação) |
| 10 | J | **CNPJ** | Texto (`XX.XXX.XXX/XXXX-XX`) | Planilha (manual/importação) |
| 11 | K | Razão Social | Texto | Planilha (manual/importação) |
| 14 | N | **Mês Anterior - Fiscal** | Fração de dia `[h]:mm:ss` | Script (backfill) |
| 15 | O | **Horário Fiscal** | Fração de dia `[h]:mm:ss` | Script (Fiscal) |
| 16 | P | **Horário Contábil** | Fração de dia `[h]:mm:ss` | Script (Contábil) |
| 17 | Q | **Horário Pessoal (DP)** | Fração de dia ou texto | Script (Folha) |
| 18 | R | **Total** (`=O+P+Q`) | Fórmula Excel | Script (final) |

> **Formato das células de tempo:** Todas as colunas N, O, P, Q, R devem usar o formato `[h]:mm:ss` para suportar valores acima de 24 horas.

---

## 3. Identificação de Clientes — Lookup Duplo

Para garantir que **nenhum cliente seja omitido** e que **conflitos de CNPJ duplicado sejam detectados**, a identificação do cliente na planilha usa **duas variáveis redundantes**:

```
1ª Variável: Código Domínio → Coluna H (codi_emp)
2ª Variável: CNPJ           → Coluna J (cnpj_emp)
```

### Algoritmo de Lookup

```python
def encontrar_linha_cliente(sh, codi_emp: int, cnpj: str) -> int | None:
    """
    Localiza a linha de um cliente na planilha Master usando lookup duplo.
    Tenta primeiro pelo Código Domínio (H), depois pelo CNPJ (J).
    Se ambos falharem, o cliente não está na planilha.

    Args:
        sh: Objeto Worksheet (openpyxl) da aba mensal.
        codi_emp: Código Domínio do cliente (inteiro).
        cnpj: CNPJ do cliente (string, pode conter formatação).

    Returns:
        Número da linha encontrada (1-indexed) ou None se não encontrado.
    """
    cnpj_limpo = re.sub(r'\D', '', cnpj)  # Remove pontos, barras e traço

    for row in sh.iter_rows(min_row=10):
        # 1ª tentativa: Código Domínio (coluna H, index 7)
        cod_cell = row[7].value
        if cod_cell and str(cod_cell).strip() == str(codi_emp):
            return row[0].row

        # 2ª tentativa: CNPJ (coluna J, index 9)
        cnpj_cell = row[9].value
        if cnpj_cell:
            cnpj_cell_limpo = re.sub(r'\D', '', str(cnpj_cell))
            if cnpj_cell_limpo == cnpj_limpo:
                return row[0].row

    return None  # Não encontrado — cliente ausente da planilha
```

### Prioridade do Lookup

```
1º → Código Domínio (col H) — mais rápido e confiável
2º → CNPJ (col J)            — fallback robusto para casos sem código Domínio
Se nenhum match → cliente ausente da planilha (registrar em log de avisos)
```

> **Por que o CNPJ é importante?** Alguns clientes têm o campo H preenchido com textos especiais (ver seção 3.1) em vez do código numérico. Nesses casos, o CNPJ é a única forma de cruzamento automático confiável.

### Detecção de CNPJ Duplicado

Um CNPJ duplicado na planilha indica erro de cadastro (ex: mesma empresa com dois `codi_emp` distintos, ou empresa aberta novamente após encerramento). O script deve:

1. **Alertar** no log quando um mesmo CNPJ aparecer em mais de uma linha
2. **Não preencher** automaticamente nenhuma das linhas (aguardar intervenção manual)
3. **Registrar** o conflito em um arquivo de log com o CNPJ e os números de linha com conflito

```python
# Exemplo de detecção de duplicidade antes do preenchimento
from collections import defaultdict

def detectar_cnpj_duplicado(sh) -> dict:
    """
    Escaneia a planilha em busca de CNPJs duplicados.

    Returns:
        Dicionário {cnpj: [lista_de_linhas]} com apenas os CNPJs duplicados.
    """
    mapa = defaultdict(list)
    for row in sh.iter_rows(min_row=10):
        cnpj_cell = row[9].value
        if cnpj_cell:
            cnpj_limpo = re.sub(r'\D', '', str(cnpj_cell))
            if cnpj_limpo:
                mapa[cnpj_limpo].append(row[0].row)
    return {cnpj: linhas for cnpj, linhas in mapa.items() if len(linhas) > 1}
```

---

### 3.1 Valores Especiais no Campo Código Domínio (Coluna H)

A coluna H pode conter **textos especiais** em vez do código numérico. Esses valores indicam a razão pela qual o cliente não possui código no Domínio:

| Valor na Coluna H | Significado | Ação do Script |
|---|---|---|
| `Não entra - sistema próprio` | Cliente usa ERP próprio, não está no Domínio | Não buscar dados de Domínio; pular lookup por código |
| `Não esta na Dominio` | Cliente não cadastrado no Domínio | Não buscar dados de Domínio; usar CNPJ como fallback |
| `Não entra - Consultoria` | Cliente de consultoria eventual, não operacional | Não buscar dados de Domínio; verificar regras de consultoria |

> **Regra:** Se o campo H contém um desses textos especiais, o script **não deve tentar** lookup por código Domínio. Deve proceder diretamente para o lookup por CNPJ. Se o CNPJ também não estiver nos dados extraídos do banco, o cliente simplesmente não tem produtividade registrada no sistema e nenhum valor deve ser lançado.

---

## 4. Regras de Alimentação por Coluna

### 4.1 Coluna N — Mês Anterior Fiscal

> **Válido a partir de Dezembro/2025.**

**O que vai aqui:** O valor da coluna **O** (Horário Fiscal) da **aba do mês anterior** para o mesmo cliente.

**Como preencher:**
- Abrir o arquivo master
- Localizar a aba `MM-1.AAAA`
- Para cada cliente (por `codi_emp` ou CNPJ), copiar o valor da col O
- Gravar na col N da aba atual

**Quem não deve ter valor na coluna N:**
- Clientes que não existiam na aba anterior
- Primeiro mês de uso do sistema (aba 12.2025)

Ver implementação completa em [Spec_Produtividade_Fiscal.md — Seção 6.2](./Spec_Produtividade_Fiscal.md#62-backfill-do-mês-anterior-coluna-n-).

---

### 4.2 Coluna O — Horário Fiscal

**O que vai aqui:** Tempo total (em segundos convertidos) que os colaboradores ficaram no módulo Fiscal do Domínio para aquele cliente no mês, **com adicional de 80%**.

**Fórmula:**
```
segundos_brutos = SUM(DATEDIFF(second, ...)) por cliente na GELOGUSER (sist_log=5)
tempo_final = segundos_brutos × 1.80
valor_excel = tempo_final / 86400
```

**Quem NÃO recebe valor na coluna O:**
- Clientes listados como `Não entra - sistema próprio` ou `Não esta na Dominio` (sem dados na GELOGUSER)
- Clientes inexistentes na aba do mês

Ver detalhes completos em [Spec_Produtividade_Fiscal.md](./Spec_Produtividade_Fiscal.md).

---

### 4.3 Coluna P — Horário Contábil

**O que vai aqui:** Tempo total de trabalho contábil, extraído da planilha `HORAS CONTABEIS.xlsx`.

**Quem NÃO recebe valor na coluna P:**
- Clientes listados em `NAO FAZ CONTABIL.txt` → recebem o texto `"NAO FAZ CONTABIL"` na coluna P
- Clientes sem cadastro na planilha de horas contábeis

> **Atenção:** Empresas no arquivo `NAO FAZ CONTABIL.txt` identificadas com `Não entra - sistema próprio` são geridas por sistema externo à DMF. Não preencher P para essas empresas.

---

### 4.4 Coluna Q — Horário Pessoal (DP)

**O que vai aqui:** Tempo estimado de folha de pagamento, calculado com base no número de empregados ativos extraídos do Domínio.

**Fórmula:**
```
se total_empregados > 0:  Q = (total × 0,33) + 1,5  (em horas)
se total_empregados = 0:  Q = 00:05:00  (mínimo obrigatório)
```

**Quem NÃO recebe tempo calculado na coluna Q:**
- Empresas em `DP NAO.txt` **sem** flag de consultoria → recebem texto `"DP NÃO"`
- Empresas em `DP NAO.txt` **com** flag `FAZ CONSULTORIA, LANCAR APENAS 1:30` → recebem texto `"1:30"`

Ver detalhes completos em [Spec_Folha_Pagamento.md](./Spec_Folha_Pagamento.md).

---

### 4.5 Coluna R — Total

**O que vai aqui:** Soma das colunas O, P e Q.

**Regra:** Sempre manter como **fórmula Excel**, não valor estático:
```excel
=O{row}+P{row}+Q{row}
```

**Formato da célula:** `[h]:mm:ss`

> **Atenção:** Se Q ou P contiver texto (`"DP NÃO"`, `"NAO FAZ CONTABIL"`, `"1:30"`), a fórmula `=O+P+Q` vai quebrar para aquela linha. O script deve verificar antes de inserir a fórmula e, se houver texto em alguma das colunas, calcular o total manualmente ou deixar a célula em branco.

---

## 5. Sistemas de Exceção

### 5.1 DP NÃO — Empresas sem Folha de Pagamento na DMF

**Arquivo:** [`nao_faz_setor/DP NAO.txt`](./nao_faz_setor/DP%20NAO.txt)

#### Formatos de linha no arquivo

| Formato | Exemplo | Ação |
|---|---|---|
| Apenas nome (sem código) | `AGRO EMPRESA FANTASIA LTDA` | Match por nome na col I ou K |
| `CÓDIGO\tNOME` | `988\tLE BRUT INDUSTRIA...` | Match prioritário por código (col H) |
| `CÓDIGO;NOME` | `853;PET SHOP FANTASIA LTDA` | Match por código (separador `;`) |
| `CÓDIGO\tNOME (FAZ CONSULTORIA...)` | `1107 GLOBAL...` | Lança `"1:30"` no campo Q |
| `Não entra - sistema próprio\tNOME` | Sem código numérico | Match por nome; não consultar Domínio |

#### Resultado na planilha

| Flag no arquivo | Valor lançado em Q | Observação |
|---|---|---|
| Sem flag | `"DP NÃO"` | Não calcular fórmula de empregados |
| `FAZ CONSULTORIA, LANCAR APENAS 1:30` | `"1:30"` | Overhead fixo de consultoria |
| `Não entra - sistema próprio` | `"DP NÃO"` | Sistema externo |

#### Exemplos de empresas no arquivo DP NAO.txt

| Código | Nome | Observação |
|---|---|---|
| — | AGRO EMPRESA FANTASIA LTDA | Match por nome |
| 988-1012 | LE BRUT INDUSTRIA E COMERCIO DE ROUPAS | Múltiplos CNPJs/filiais |
| 993 | LE BRUT ... | Consultoria: `"1:30"` |
| 853–856 | PET SHOP FANTASIA LTDA | Várias filiais |
| 837 | PET SHOP FANTASIA LTDA | Consultoria: `"1:30"` |
| 1107 | CONSTRUTORA FANTASIA LTDA | Consultoria: `"1:30"` |

---

### 5.2 NÃO FAZ CONTÁBIL — Empresas sem Contabilidade na DMF

**Arquivo:** [`nao_faz_setor/NAO FAZ CONTABIL.txt`](./nao_faz_setor/NAO%20FAZ%20CONTABIL.txt)

#### Formatos de linha no arquivo

| Formato | Exemplo | Ação |
|---|---|---|
| `CÓDIGO\tNOME` | `603\tHOLDING FANTASIA LTDA` | Match por código (col H) |
| `Não esta na Dominio\tNOME` | `Não esta na Dominio\tPATRIMONIAL FANTASIA LTDA` | Match por nome |
| `Não entra - sistema próprio\tNOME` | Sem código numérico | Match por nome; não consultar Domínio |

#### Resultado na planilha

- A coluna **P** recebe o texto `"NAO FAZ CONTABIL"` para esses clientes
- **Não lançar** tempo contábil calculado

#### Exemplos de empresas no arquivo NAO FAZ CONTABIL.txt

| Código | Nome |
|---|---|
| — | PATRIMONIAL FANTASIA LTDA (não está na Domínio) |
| 603 | HOLDING FANTASIA LTDA |
| 19 | ENGENHARIA FANTASIA LTDA |
| 58 | CONSTRUTORA EXEMPLO LTDA |
| 360 | POSTO DE GASOLINA FANTASIA LTDA |
| — | MC4, HEY MAN, MILL, BFW... (sistema próprio) |

---

## 6. Pipeline Geral de Preenchimento

A sequência correta de preenchimento da planilha master a cada mês:

```
┌─────────────────────────────────────────────────────────────┐
│            PIPELINE GERAL — PLANILHA MASTER                 │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────┐
  │  0. PRÉ-VERIFICAÇÕES                                 │
  │     - Detectar CNPJs duplicados na aba atual         │
  │     - Log de avisos para intervenção manual          │
  └───────────────────┬──────────────────────────────────┘
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  1. BACKFILL COLUNA N (Mês Anterior Fiscal)          │
  │     Copiar col O da aba MM-1 → col N da aba atual    │
  │     Match por: codi_emp primeiro, CNPJ como fallback │
  │     (válido a partir de 12.2025)                     │
  └───────────────────┬──────────────────────────────────┘
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  2. PREENCHER COLUNA O (Horário Fiscal)              │
  │     Fonte: GELOGUSER sist_log=5, DATEDIFF(second)    │
  │     Aplicar adicional 80% antes de gravar            │
  │     Match: codi_emp → CNPJ                           │
  └───────────────────┬──────────────────────────────────┘
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  3. PREENCHER COLUNA P (Horário Contábil)            │
  │     Fonte: Planilha HORAS CONTABEIS                  │
  │     Exceção: "NAO FAZ CONTABIL" para lista específica│
  └───────────────────┬──────────────────────────────────┘
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  4. PREENCHER COLUNA Q (Horário Pessoal / DP)        │
  │     Fonte: Domínio (foempregados) + fórmula          │
  │     Exceção: "DP NÃO" ou "1:30" para lista específica│
  └───────────────────┬──────────────────────────────────┘
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  5. PREENCHER COLUNA R (Total)                       │
  │     Fórmula: =O+P+Q                                  │
  │     Verificar se O, P, Q são numéricos antes         │
  │     Formato: [h]:mm:ss                               │
  └───────────────────┬──────────────────────────────────┘
                      ▼
  ┌──────────────────────────────────────────────────────┐
  │  6. SALVAR E VALIDAR                                 │
  │     - Salvar como .xlsm (preservar macros)           │
  │     - Log de clientes sem match (aviso)              │
  │     - Log de clientes com CNPJ duplicado (erro)      │
  └──────────────────────────────────────────────────────┘
```

---

## 7. Regras de Ouro (O que NÃO fazer)

> Estas regras evitam corrupção de dados, conflitos de fórmulas e retrabalho.

| ❌ NÃO fazer | ✅ Fazer |
|---|---|
| Salvar como `.xlsx` (perde macros) | Sempre salvar como `.xlsm` |
| Preencher coluna R com valor estático | Sempre usar fórmula `=O{row}+P{row}+Q{row}` |
| Usar `DATEDIFF(minute)` para Fiscal | Usar `DATEDIFF(second)` e converter |
| Buscar cliente apenas pelo código H | Usar lookup duplo: H → J (CNPJ) |
| Ignorar clientes com H = texto especial | Tratar os 3 valores especiais (ver seção 3.1) |
| Aplicar o adicional de 80% antes de salvar os segundos brutos | Salvar bruto no dict, aplicar 80% apenas na conversão para Excel |
| Preencher O para clientes `"Não esta na Dominio"` | Pular esses clientes na extração do Domínio |
| Preencher P para clientes em `NAO FAZ CONTABIL.txt` | Lançar texto `"NAO FAZ CONTABIL"` |
| Preencher Q para clientes em `DP NAO.txt` (sem consultoria) | Lançar texto `"DP NÃO"` |
| Fazer lookup apenas por nome (col I ou K) sem tentar H e J primeiro | Seguir a hierarquia: H → J → nome |

---

## 8. Relação com os outros Specs

Esta planilha é **resultado** de três processos independentes descritos em specs separados. As regras de cada coluna **não devem conflitar**:

| Spec | Coluna alimentada | Restrições cruzadas |
|---|---|---|
| [Spec_Produtividade_Fiscal.md](./Spec_Produtividade_Fiscal.md) | O e N | O adicional de 80% é aplicado ANTES de gravar em O. N recebe o valor de O do mês anterior **já com** o adicional. |
| [Spec_Folha_Pagamento.md](./Spec_Folha_Pagamento.md) | Q | Empresas em `DP NAO.txt` recebem texto, não valor numérico. Não conflita com O ou P. |
| **Este Spec** | N, O, P, Q, R | Define a sequência de preenchimento, o lookup duplo e as regras de proteção globais. |

> **Regra de autoridade:** Em caso de conflito aparente, este Spec define a **ordem de preenchimento** e as **regras de lookup**. Os outros Specs definem **como calcular** o valor de cada coluna.

---

## 9. Scripts e Arquivos do Projeto

| Arquivo | Descrição | Status |
|---|---|---|
| [`processar_horas.py`](./processar_horas.py) | Pipeline principal — integra Fiscal, Contábil e Folha na planilha master | 🔄 Integração Fiscal pendente |
| [`extrair_fiscal_direto.py`](./extrair_fiscal_direto.py) | Extração de produtividade Fiscal (col O) | ✅ Validado Jan/2026 |
| [`nao_faz_setor/DP NAO.txt`](./nao_faz_setor/DP%20NAO.txt) | Lista de empresas sem Folha na DMF | ✅ Arquivo de referência |
| [`nao_faz_setor/NAO FAZ CONTABIL.txt`](./nao_faz_setor/NAO%20FAZ%20CONTABIL.txt) | Lista de empresas sem Contabilidade na DMF | ✅ Arquivo de referência |
| `CONTROLE_DE_HORAS_DMF.xlsm` | Planilha Master (arquivo resultante) | Manual — não versionar |

---

## Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 2026-03-11 | Criação do spec. Mapeamento completo de colunas, lookup duplo (H + J), valores especiais, regras de exceção e pipeline de preenchimento. |
