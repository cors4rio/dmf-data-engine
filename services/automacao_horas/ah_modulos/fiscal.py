import logging
from ah_engine.database import db
from ah_modulos.excecoes import ler_codigos_setor

def extrair_e_preencher_fiscal(writer, data_inicio, data_fim, adicional_pct=80):
    """
    Extrai horas gastas no Domínio Fiscal (GELOGUSER)
    Aplica o adicional configurado na UI (padrão 80%) e envia para a Master (Coluna O).
    """
    logging.info(f"[FISCAL] Iniciando extração de dados fiscais com +{adicional_pct}% de adicional...")
    
    query = """
    SELECT 
        e.codi_emp,
        SUM(
            DATEDIFF(second,
                YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tini_log,
                COALESCE(
                    YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log,
                    YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log
                )
            )
        ) AS total_segundos
    FROM 
        bethadba.geloguser l
    INNER JOIN 
        bethadba.geempre e ON e.codi_emp = l.codi_emp
    WHERE 
        l.sist_log = 5
        AND l.tfim_log IS NOT NULL
        AND l.data_log >= ?
        AND l.data_log <= ?
    GROUP BY 
        e.codi_emp
    """
    
    resultados = db.fetch_all(query, (data_inicio, data_fim))
    
    if not resultados:
        logging.warning("[FISCAL] Nenhum dado retornado do Domínio.")
        return False

    FATOR = 1.0 + (float(adicional_pct) / 100.0)

    excecoes = ler_codigos_setor("fiscal")
    if excecoes:
        logging.info(f"[FISCAL] {len(excecoes)} código(s) na lista FISCAL_NAO serão ignorados.")

    contador = 0
    descartadas_null = 0
    descartadas_erro = 0
    excluidas_excecao = 0
    for row in resultados:
        cod_emp = row.get('codi_emp')
        total_segundos = row.get('total_segundos')

        if cod_emp is None:
            descartadas_null += 1
            continue
        if total_segundos is None:
            descartadas_null += 1
            logging.debug(f"[FISCAL] codi_emp={cod_emp} sem total_segundos (Null). Pulando.")
            continue

        try:
            cod_str = str(int(float(str(cod_emp))))
            if cod_str in excecoes:
                excluidas_excecao += 1
                continue
            segundos_bruto = float(total_segundos)
            segundos_final = segundos_bruto * FATOR
            valor_excel = segundos_final / 86400.0
            writer.preencher_fiscal(cod_str, valor_excel)
            contador += 1
        except (ValueError, TypeError) as e:
            descartadas_erro += 1
            logging.warning(f"[FISCAL] Linha descartada (codi_emp={cod_emp!r}, total={total_segundos!r}): {e}")

    logging.info(
        f"[FISCAL] Finalizado. {contador} empresas preenchidas · "
        f"{descartadas_null} sem dados · {descartadas_erro} com erro · "
        f"{excluidas_excecao} excluídas por FISCAL_NAO · fator +{adicional_pct}%."
    )
    return True
