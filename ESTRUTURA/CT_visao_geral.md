#  Módulo Contábil (CT) — Visão Geral

<!-- META PARA LLMs
  Prefixo: CT
  Módulo:  Contábil
  Schema:  bethadba
  Chave:   codi_emp
  Contexto: Lançamentos contábeis, plano de contas, conciliação bancária, SPED ECF
-->

> O módulo **CT (Contábil)** contém lançamentos, plano de contas, balanço e os
> parâmetros de SPED (SPED Contábil e ECF). É usado para auditoria de quantidade de
> movimentações por empresa.

---

## Tabelas Principais

| Tabela | Linhas (aprox.) | Descrição |
|--------|-----------------|-----------|
| `bethadba.ctlancto` | Alta |  **Lançamentos contábeis** — filtro: `data_lan` |
| `bethadba.ctparmto_sped_vigencia` | — | Parâmetros SPED ECF — validação de regime |
| `bethadba.CTCONCILIACAO_BANCARIA` | 877.206 | Conciliação bancária |
| `bethadba.CTBAKLANCTOLOTE` | 339.395 | Backup de lotes de lançamentos |
| `bethadba.CTCONTAS_ANEEL` | 8.998 | Plano de contas ANEEL |
| `bethadba.CTCONTAS_ANS` | 17.576 | Plano de contas ANS |
| `bethadba.CTCOEFICIENTE` | 27 | Coeficientes para índices financeiros |

---

## Campo `orig_lan` — Origem do Lançamento

Na tabela `ctlancto`, o campo `orig_lan` identifica o tipo de lançamento:

| Código | Tipo de Lançamento |
|:------:|--------------------|
| `1` | Lançamento Normal |
| `5` | Extrato Bancário |
| outros | Outros tipos (automáticos, importação etc) |

---

## Padrão de Filtro por Período

```sql
-- Lançamentos de janeiro de 2026
SELECT codi_emp, COUNT(*) AS Total_Lancamentos
FROM bethadba.ctlancto
WHERE data_lan >= '2026-01-01'
  AND data_lan <= '2026-01-31'
GROUP BY codi_emp;
```
