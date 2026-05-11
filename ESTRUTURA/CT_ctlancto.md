#  `bethadba.ctlancto` — Lançamentos Contábeis

<!-- META PARA LLMs
  Tabela:      bethadba.ctlancto
  Módulo:      CT (Contábil)
  Propósito:   Lançamentos contábeis por empresa e período
  Filtro Data: data_lan
  Chave:       codi_emp + nume_lan (número do lançamento)
  Campo-chave: orig_lan (1=Normal, 5=Extrato Bancário)
-->

## Descrição

Tabela principal de **lançamentos contábeis**. Cada linha representa um lançamento
(débito/crédito) realizado pelo contador. É a base para contar o volume de trabalho
por empresa em determinado período.

---

## Colunas Principais

| Coluna | Tipo | Nullable | Descrição |
|--------|------|:--------:|-----------|
| `codi_emp` | `integer` |  | FK → `geempre.codi_emp` |
| `data_lan` | `date` |  | **Data do lançamento** ← filtro principal |
| `orig_lan` | `smallint` |  | **Origem:** `1`=Normal, `5`=Extrato Bancário |
| `nume_lan` | `integer` |  | Número sequencial do lançamento |
| `codi_lote` | `integer` |  | Lote do lançamento |
| `fili_lan` | `integer` |  | Filial |
| `val_lan` | `numeric` |  | Valor do lançamento |
| `hist_lan` | `varchar` |  | Histórico/descrição do lançamento |

---

## Queries

### Quantidade de lançamentos por empresa no mês
```sql
SELECT 
    codi_emp                                                AS Codigo_Cliente,
    SUM(CASE WHEN orig_lan = 1 THEN 1 ELSE 0 END)          AS Lancamentos_Normal,
    SUM(CASE WHEN orig_lan = 5 THEN 1 ELSE 0 END)          AS Lancamentos_Extrato_Bancario,
    COUNT(*)                                                AS Total_Lancamentos_Gerais
FROM bethadba.ctlancto
WHERE data_lan >= '{{DATA_INICIO_MES}}'
  AND data_lan <= '{{DATA_FIM_MES}}'
GROUP BY codi_emp
HAVING SUM(CASE WHEN orig_lan IN (1, 5) THEN 1 ELSE 0 END) > 0
ORDER BY codi_emp;
```

### Total de lançamentos de uma empresa específica
```sql
SELECT 
    data_lan,
    orig_lan,
    COUNT(*) AS Quantidade
FROM bethadba.ctlancto
WHERE codi_emp = 1233
  AND data_lan >= '2026-01-01'
  AND data_lan <= '2026-01-31'
GROUP BY data_lan, orig_lan
ORDER BY data_lan;
```

---

## Armadilhas

|  Problema |  Solução |
|------------|-----------|
| Incluir `orig_lan` de outros valores no total | Filtrar apenas `1` e `5` para contagem de movimentos do escritório |
| Contar duplicatas por filial | Verificar campo `fili_lan` |
