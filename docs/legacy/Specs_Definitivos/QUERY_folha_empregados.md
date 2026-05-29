# Query — Empregados Ativos por Competência (Folha DP)

<!-- META PARA LLMs
  Propósito: Contar empregados ativos por empresa em um mês específico para cálculo de horas de DP
  Tabelas:   foempregados (admissão) + forescisoes (rescisão/demissão)
  Variáveis: {{DATA_INICIO_MES}}, {{DATA_FIM_MES}}
  Validada:  SIM — testado em Janeiro/2026 para empresas 8001 (ADRIANA) e 856 (AGROMIX)
             Resultado bateu com realidade: 11 e 6 respectivamente
-->

## Conclusão da Validação (Março/2026)

| Empresa | Realidade Jan/2026 | Resultado Domínio (bruto) | Resultado Domínio (cruzado c/ forescisoes) |
|---|---|---|---|
| **8001 ADRIANA** | **11** | 21 ❌ | **11** ✅ |
| **856 AGROMIX** | **6** | 13 ❌ | **6** ✅ |

> ⚠️ **A tabela `foempregados` acumula histórico de TODOS que já passaram pela empresa.**
> Sem o cruzamento com `forescisoes`, o banco retorna histórico de ex-funcionários.
> **O cruzamento com `forescisoes` é obrigatório para bater com a realidade.**

---

## Mapeamento de Vínculo (`vinculo` em `foempregados`)

| Código | Tipo | Obs |
|---|---|---|
| `1` | **Funcionário** (CLT) | ~35.900 no banco |
| `6` | **Estagiário** | ~125 no banco |
| `11` | **Contribuinte Individual** | ~1.800 no banco |
| Outros | Demais vínculos | Não entram no cálculo |

> ✅ Todos os três tipos somam para a fórmula de horas DP.

---

## Query Principal Validada — Cruzamento foempregados + forescisoes

> **Ativo no mês = está em `foempregados` E NÃO está em `forescisoes` com demissão antes do mês**

```sql
SELECT
    e.codi_emp                                                        AS Codigo_Cliente,
    SUM(CASE WHEN e.vinculo = 1  THEN 1 ELSE 0 END)                  AS Qtd_Funcionarios,
    SUM(CASE WHEN e.vinculo = 6  THEN 1 ELSE 0 END)                  AS Qtd_Estagiarios,
    SUM(CASE WHEN e.vinculo = 11 THEN 1 ELSE 0 END)                  AS Qtd_Contribuintes,
    SUM(CASE WHEN e.vinculo IN (1, 6, 11) THEN 1 ELSE 0 END)         AS Total_Para_Formula

FROM bethadba.foempregados e

-- Exclui quem foi demitido ANTES do início do mês
LEFT JOIN bethadba.forescisoes r
    ON r.codi_emp = e.codi_emp
   AND r.i_empregados = e.i_empregados
   AND r.demissao < '{{DATA_INICIO_MES}}'

WHERE e.admissao <= '{{DATA_FIM_MES}}'   -- Admitido até o fim do mês
  AND r.i_empregados IS NULL             -- Sem rescisão anterior ao início do mês

GROUP BY e.codi_emp
ORDER BY e.codi_emp;
```

**Parâmetros N8N:**
- `{{DATA_INICIO_MES}}` → ex: `2026-01-01`
- `{{DATA_FIM_MES}}` → ex: `2026-01-31`

**Lógica:**
- `admissao <= fim_do_mes` → admitido antes ou durante o mês
- `LEFT JOIN + IS NULL` → filtra somente quem **não** tem rescisão registrada antes do início do mês
  - Se `demissao < DATA_INICIO_MES`: excluído (saiu antes do mês começar)
  - Se `demissao >= DATA_INICIO_MES`: ainda conta no mês (saiu durante ou depois)
  - Se não há registro em `forescisoes`: ainda ativo

---

## Query com Indicador Booleano — TEM FOLHA?

```sql
SELECT
    g.codi_emp,
    g.nome_emp,
    CASE WHEN COALESCE(f.total, 0) > 0 THEN 'SIM' ELSE 'NAO' END AS Tem_Folha,
    COALESCE(f.func,   0)  AS Qtd_Funcionarios,
    COALESCE(f.estag,  0)  AS Qtd_Estagiarios,
    COALESCE(f.contrib,0)  AS Qtd_Contribuintes,
    COALESCE(f.total,  0)  AS Total_Para_Formula
FROM bethadba.geempre g
LEFT JOIN (
    SELECT
        e.codi_emp,
        SUM(CASE WHEN e.vinculo = 1  THEN 1 ELSE 0 END) AS func,
        SUM(CASE WHEN e.vinculo = 6  THEN 1 ELSE 0 END) AS estag,
        SUM(CASE WHEN e.vinculo = 11 THEN 1 ELSE 0 END) AS contrib,
        SUM(CASE WHEN e.vinculo IN (1,6,11) THEN 1 ELSE 0 END) AS total
    FROM bethadba.foempregados e
    LEFT JOIN bethadba.forescisoes r
        ON r.codi_emp      = e.codi_emp
       AND r.i_empregados  = e.i_empregados
       AND r.demissao      < '{{DATA_INICIO_MES}}'
    WHERE e.admissao <= '{{DATA_FIM_MES}}'
      AND r.i_empregados IS NULL
    GROUP BY e.codi_emp
) f ON g.codi_emp = f.codi_emp
ORDER BY g.codi_emp;
```

---

## Regra de Mínimo (Clientes Zerados)

> Empresas que fazem DP mas têm **zero empregados ativos** no mês recebem **00:05:00** (5 minutos) — não zero.

```python
MINUTO_5 = 5 / 60 / 24  # fração de dia para Excel = 00:05:00

if total_para_formula > 0:
    horas = (total_para_formula * 0.33) + 1.5
else:
    horas = 5 / 60  # mínimo obrigatório: 5 minutos
```

---

## Fallback — Planilha Carol

Se os dados do Domínio não baterem com a realidade há algum erro de lançamento ou mês desatualizado.

- **Arquivo:** `Controle de Empregados MM(CAROL).xls`
- **Colunas de referência:** índices `[7, 9, 11, 13, 15, 17, 19, 21, 23]`
- A Carol é **fallback de validação** — a fonte primária é sempre o Domínio.
