#  `bethadba.ctparmto_sped_vigencia` — Parâmetros SPED ECF

<!-- META PARA LLMs
  Tabela:    bethadba.ctparmto_sped_vigencia
  Módulo:    CT (Contábil)
  Propósito: Parâmetros de SPED ECF — fonte SECUNDÁRIA de validação do regime tributário
  Campo-chave: forma_tributacao (5=Presumido, 6=Real)
  Prioridade: MENOR que efparametro_vigencia.rfed_par — usar apenas para confirmação
-->

## Descrição

Parâmetros do SPED para fins de ECF (Escrituração Contábil Fiscal). Usada como
**segunda fonte** de validação do regime tributário, especialmente para Lucro Presumido e Real.

>  **Prioridade:** Use sempre `efparametro_vigencia.rfed_par` como fonte primária.
> Esta tabela é útil apenas para **confirmar** o regime em auditorias de SPED.

---

## Colunas Principais

| Coluna | Tipo | Nullable | Descrição |
|--------|------|:--------:|-----------|
| `codi_emp` | `integer` |  | FK → `geempre.codi_emp` |
| `vigencia` | `date` |  | Data de início de vigência |
| `forma_tributacao` | `smallint` |  | `5`=Lucro Presumido, `6`=Lucro Real |

---

## Mapeamento `forma_tributacao`

| Código | Regime |
|:------:|--------|
| `5` | Lucro Presumido |
| `6` | Lucro Real |
| outros | Verificar caso a caso |

---

## Query de Validação Cruzada

```sql
-- Verificar consistência entre as duas tabelas de regime
SELECT 
    e.codi_emp,
    e.nome_emp,
    CASE ef.rfed_par
        WHEN 5 THEN 'Presumido (EF)'
        WHEN 1 THEN 'Real (EF)'
        ELSE CAST(ef.rfed_par AS VARCHAR)
    END AS Regime_Fiscal,
    CASE ct.forma_tributacao
        WHEN 5 THEN 'Presumido (CT)'
        WHEN 6 THEN 'Real (CT)'
        ELSE CAST(ct.forma_tributacao AS VARCHAR)
    END AS Regime_Sped
FROM bethadba.geempre e
LEFT JOIN bethadba.efparametro_vigencia ef ON e.codi_emp = ef.codi_emp
    AND ef.vigencia_par = (SELECT MAX(vigencia_par) FROM bethadba.efparametro_vigencia
                           WHERE codi_emp = e.codi_emp AND vigencia_par <= CURRENT DATE)
LEFT JOIN bethadba.ctparmto_sped_vigencia ct ON e.codi_emp = ct.codi_emp
    AND ct.vigencia = (SELECT MAX(vigencia) FROM bethadba.ctparmto_sped_vigencia
                       WHERE codi_emp = e.codi_emp AND vigencia <= CURRENT DATE)
WHERE ef.rfed_par IN (1, 5)  -- Apenas Presumido e Real (os que têm ECF)
ORDER BY e.codi_emp;
```
