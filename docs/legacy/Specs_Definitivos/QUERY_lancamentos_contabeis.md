#  Query — Lançamentos Contábeis

<!-- META PARA LLMs
  Propósito: Contar lançamentos contábeis (Normal e Extrato Bancário) por empresa/mês
  Tabelas:   ctlancto
  Variáveis: {{DATA_INICIO_MES}}, {{DATA_FIM_MES}}
  Validada:  Sim (uso em produção na planilha contábil DMF)
-->

## Query Principal

```sql
SELECT 
    codi_emp                                                   AS Codigo_Cliente,
    SUM(CASE WHEN orig_lan = 1 THEN 1 ELSE 0 END)             AS Lancamentos_Normal,
    SUM(CASE WHEN orig_lan = 39 THEN 1 ELSE 0 END)            AS Lancamentos_Extrato_Bancario,
    COUNT(*)                                                   AS Total_Lancamentos_Gerais
FROM bethadba.ctlancto
WHERE data_lan >= '{{DATA_INICIO_MES}}'
  AND data_lan <= '{{DATA_FIM_MES}}'
  AND orig_lan IN (1, 39)
GROUP BY codi_emp
ORDER BY codi_emp;
```

## Legenda `orig_lan`
| Código | Tipo |
|:------:|------|
| 1 | Lançamento Normal |
| 39 | Conciliação Bancária (Extrato Bancário) |
| outros | Integrações / Automáticos |
