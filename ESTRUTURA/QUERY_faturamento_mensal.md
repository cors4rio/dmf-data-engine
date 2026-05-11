#  Query — Faturamento Mensal

<!-- META PARA LLMs
  Propósito: Calcular faturamento mensal total = vendas (efsaidas) + serviços (efservicos)
  Tabelas:   efsaidas, efservicos
  Variáveis: {{DATA_INICIO_MES}}, {{DATA_FIM_MES}}
  Validada:  Sim (uso em produção na planilha contábil DMF)
-->

## Query Principal (Vendas + Serviços)

```sql
SELECT 
    codi_emp            AS Codigo_Cliente,
    SUM(total_contabil) AS Faturamento_Mensal
FROM (
    SELECT codi_emp, SUM(vcon_sai) AS total_contabil
    FROM bethadba.efsaidas
    WHERE dsai_sai >= '{{DATA_INICIO_MES}}'
      AND dsai_sai <= '{{DATA_FIM_MES}}'
    GROUP BY codi_emp

    UNION ALL

    SELECT codi_emp, SUM(vcon_ser) AS total_contabil
    FROM bethadba.efservicos
    WHERE dser_ser >= '{{DATA_INICIO_MES}}'
      AND dser_ser <= '{{DATA_FIM_MES}}'
    GROUP BY codi_emp
) base
GROUP BY codi_emp
ORDER BY codi_emp;
```

## Query Separada (Vendas e Serviços)

```sql
SELECT 
    COALESCE(s.codi_emp, sv.codi_emp) AS Codigo_Cliente,
    COALESCE(s.vendas, 0)             AS Faturamento_Vendas,
    COALESCE(sv.servicos, 0)          AS Faturamento_Servicos,
    COALESCE(s.vendas, 0) + COALESCE(sv.servicos, 0) AS Total
FROM (
    SELECT codi_emp, SUM(vcon_sai) AS vendas
    FROM bethadba.efsaidas
    WHERE dsai_sai BETWEEN '{{DATA_INICIO_MES}}' AND '{{DATA_FIM_MES}}'
    GROUP BY codi_emp
) s
FULL OUTER JOIN (
    SELECT codi_emp, SUM(vcon_ser) AS servicos
    FROM bethadba.efservicos
    WHERE dser_ser BETWEEN '{{DATA_INICIO_MES}}' AND '{{DATA_FIM_MES}}'
    GROUP BY codi_emp
) sv ON s.codi_emp = sv.codi_emp
ORDER BY COALESCE(s.codi_emp, sv.codi_emp);
```
