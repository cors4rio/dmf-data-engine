# Query de Validação: Quantidade de Estagiários (Mês 01)

Esta query simula o campo calculado `quantidade_est_calc` para validar os dados do relatório com base no mês de Janeiro/2026.

## SQL Query

```sql
SELECT 
    codi_emp                AS Codigo_Empresa,
    COUNT(*)                AS quantidade_est_calc
FROM bethadba.foempregados
WHERE 
    -- Filtro de Categoria: 901 é o código padrão eSocial para Estagiários
    -- Pode variar se a empresa usar categorias customizadas, mas 103/901 são as bases.
    (categoria = 901 OR vinculo = 6) 
    
    -- Regra de Ativos em Janeiro/2026
    AND admissao <= '2026-01-31'
    AND (demissao IS NULL OR demissao >= '2026-01-01')
GROUP BY codi_emp
ORDER BY codi_emp;
```

## Detalhes Técnicos
- **Tabela**: `bethadba.foempregados`
- **Ano Base**: 2026 (assumido pelo contexto do sistema)
- **Mês**: 01
- **Lógica**: Conta todos os funcionários com vínculo de estágio que possuam data de admissão anterior ou igual ao fim de Janeiro e que não tenham sido demitidos antes do início de Janeiro.
