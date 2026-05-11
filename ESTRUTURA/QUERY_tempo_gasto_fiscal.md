<!-- META PARA LLMs
Módulo: Geral / Cadastros (GE) e Fiscal (EF)
Tags: SQL, Produtividade, Tempo, Login, Usuario, Empresa
Propósito: Retornar o tempo total gasto (em minutos) por cada colaborador em cada empresa dentro de um módulo específico (padrão: 5 = Escrita Fiscal) durante um mês.
Referência: Tabelas GELOGUSER, GEEMPRE. Tabela GEMODULOS (implícita).
Dificuldade: Média (Necessário cuidado com campos de TIME e DATE cruzando meia-noite no Sybase).
-->

#  SQL: Tempo Gasto por Usuário/Empresa no Módulo Fiscal

Esta query extrai o tempo exato (em minutos) que cada colaborador ficou ativo/logado trabalhando dentro de uma determinada empresa **especificamente** no Módulo Fiscal da Domínio (módulo 5 na `SIST_LOG`). Utilizamos dados brutos de auditoria e cálculo seguro para evitar "vazamentos" de minutos na transição de um dia para outro.

###  As Tabelas Chave
* `bethadba.geloguser`: Contém todos os registros de login, relogin e trocas de emrpesa/módulo.
* `bethadba.geempre`: Cadastro principal de empresas para resgatar o nome amigável do cliente.

###  A Query

```sql
SELECT 
    l.usua_log AS Colaborador,
    e.codi_emp AS Codigo_Cliente,
    e.nome_emp AS Nome_Cliente,
    -- Constrói o TIMESTAMP combinando DATE e TIME nativamente no Sybase, e calcula a diferença em minutos
    SUM(
        DATEDIFF(minute, 
            YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tini_log, 
            COALESCE(
				YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log, 
				YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log
			)
        )
    ) as Minutos_Gastos_Fiscal
FROM bethadba.geloguser l
INNER JOIN bethadba.geempre e 
    ON e.codi_emp = l.codi_emp
WHERE l.sist_log = 5 -- Código 5 = 'Escrita Fiscal' (Conforme GEMODULOS/GEGERENCIA_VERSAO)
  AND l.data_log >= '2025-12-01' 
  AND l.data_log <= '2025-12-31'
  AND l.tfim_log IS NOT NULL
GROUP BY 
    l.usua_log,
    e.codi_emp,
    e.nome_emp
ORDER BY 
    l.usua_log,
    Minutos_Gastos_Fiscal DESC;
```

###  Armadilhas e Truques (Gotchas)

1. **Campos Time**: Cuidado, a tabela armazena a data (`data_log` e `dfim_log`) separada da hora (`tini_log` e `tfim_log`). Fazer `DATEDIFF(minute, tini_log, tfim_log)` diretamente causará variação com valores **negativos** se o usuário trabalhar passando da meia-noite para o dia seguinte. Por isso usamos `YMD(...) + TIME` para forçar o casting para `TIMESTAMP` ou `DATETIME` do Sybase.
2. **Crash/Timeout do Sistema (tfim_log = NULL)**: Quando o sistema cai ou a máquina reinicia do nada, a coluna `tfim_log` pode não ser salva, gerando `NULL`. Na query, estamos descartando as sessões sujas com `AND l.tfim_log IS NOT NULL`, pois sessões crashadas não duram tempo infinito.
3. **Módulos (`sist_log`)**: 
   * `5` = Fiscal
   * `12` = Folha (Folha de Pagamento)
   * `2` = Geral
   * `14` = Contabilidade
