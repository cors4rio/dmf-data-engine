# QUERIES SQL PARA N8N - PROJETO PLANILHA CONTÁBIL

Estas consultas foram desenhadas e validadas para extrair os indicadores diretamente do **Banco de Dados Domínio Sistemas (via ODBC)**, substituindo o uso de planilhas locais.

As variáveis `{{DATA_INICIO_MES}}` e `{{DATA_FIM_MES}}` devem ser substituídas dinamicamente pelo N8N ao executar (ex: `2026-01-01` e `2026-01-31`).

---

### 1. QUANTIDADE DE LANÇAMENTOS CONTÁBEIS
**Regra:** Soma dos lançamentos Normais e de Extratos Bancários por Empresa em determinado mês.
**Tabela:** `bethadba.ctlancto`

```sql
SELECT 
    codi_emp as Codigo_Cliente,
    SUM(CASE WHEN orig_lan = 1 THEN 1 ELSE 0 END) as Lancamentos_Normal,
    SUM(CASE WHEN orig_lan = 39 THEN 1 ELSE 0 END) as Lancamentos_Extrato_Bancario,
    COUNT(*) as Total_Lancamentos_Gerais
FROM 
    bethadba.ctlancto
WHERE 
    data_lan >= '{{DATA_INICIO_MES}}' 
    AND data_lan <= '{{DATA_FIM_MES}}'
GROUP BY 
    codi_emp
HAVING 
    SUM(CASE WHEN orig_lan IN (1, 39) THEN 1 ELSE 0 END) > 0
ORDER BY 
    codi_emp;
```

---

### 2. FATURAMENTO DO MÊS (PRODUTOS + SERVIÇOS)
**Regra:** Soma do Valor Contábil (`vcon_sai`) das Notas de Saída e Valor Contábil (`vcon_ser`) dos Serviços no mês indicado.
**Variáveis N8N:** Substituir `{{DATA_INICIO_MES}}` e `{{DATA_FIM_MES}}`.
**Tabela:** `bethadba.efsaidas` e `bethadba.efservicos`

```sql
SELECT 
    codi_emp as Codigo_Cliente, 
    SUM(total_contabil) as Faturamento_Mensal
FROM (
    SELECT codi_emp, SUM(vcon_sai) as total_contabil 
    FROM bethadba.efsaidas 
    WHERE dsai_sai >= '{{DATA_INICIO_MES}}' AND dsai_sai <= '{{DATA_FIM_MES}}' 
    GROUP BY codi_emp
    
    UNION ALL
    
    SELECT codi_emp, SUM(vcon_ser) as total_contabil 
    FROM bethadba.efservicos 
    WHERE dser_ser >= '{{DATA_INICIO_MES}}' AND dser_ser <= '{{DATA_FIM_MES}}' 
    GROUP BY codi_emp
) base
GROUP BY 
    codi_emp;
```

---

### 3. TEM FOLHA? (EMPREGADOS ATIVOS NO MÊS)
**Regra:** Retornar a quantidade de empregados ativos dentro da competência (admitidos antes do fim do mês e não demitidos antes do início do mês). Se a quantidade for > 0, Tem Folha = SIM.
**Tabela:** `bethadba.foempregados`

```sql
SELECT 
    codi_emp as Codigo_Cliente, 
    COUNT(*) as Qtd_Empregados_Ativos
FROM 
    bethadba.foempregados
WHERE 
    admissao <= '{{DATA_FIM_MES}}'
    AND (demissao IS NULL OR demissao >= '{{DATA_INICIO_MES}}')
GROUP BY 
    codi_emp;
```

---

### 4. REGIME TRIBUTÁRIO DETALHADO (VIGENTE NO MÊS)
**Regra:** Localiza a parametrização fiscal ativa (`vigencia_par`) mais recente até o mês base. O campo `rfed_par` traz os identificadores para (2: Simples Nacional, 4: Lucro Presumido, 8: Lucro Real, etc).
**Variáveis N8N:** Substituir `{{DATA_FIM_MES}}` (ex: `2025-01-31`).
**Tabela:** `bethadba.efparametro_vigencia`

```sql
SELECT 
    p.codi_emp as Codigo_Cliente,
    CASE p.rfed_par
        WHEN 2 THEN 'Simples Nacional'
        WHEN 4 THEN 'Lucro Presumido'
        WHEN 8 THEN 'Lucro Real'
        WHEN 5 THEN 'Imune'
        WHEN 1 THEN 'Isenta'
        WHEN 7 THEN 'Lucro Arbitrado'
        ELSE 'Outros'
    END as Regime_Vigente
FROM 
    bethadba.efparametro_vigencia p
INNER JOIN (
    SELECT codi_emp, MAX(vigencia_par) as max_vigencia
    FROM bethadba.efparametro_vigencia
    WHERE vigencia_par <= '{{DATA_FIM_MES}}'
    GROUP BY codi_emp
) ult ON p.codi_emp = ult.codi_emp AND p.vigencia_par = ult.max_vigencia;
```
*(Observação: Dependendo de como o N8N precisar cruzar esses dados, as 4 queries podem ser feitas de forma independente e unidas no próprio workflow do N8N através da chave `Codigo_Cliente`).*
