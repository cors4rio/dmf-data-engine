import logging
from engine.database import db

def extrair_e_preencher_fiscal(writer, data_inicio, data_fim):
    """
    Extrai horas gastas no Domínio Fiscal (GELOGUSER)
    Aplica 80% de adicional e envia para a Master (Coluna O).
    """
    logging.info("[FISCAL] Iniciando extração de dados fiscais (GELOGUSER)...")
    
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
        
    FATOR = 1.80 # +80% conforme Spec
    contador = 0
    for row in resultados:
        cod_emp = row.get('codi_emp')
        total_segundos = row.get('total_segundos')
        
        if cod_emp and total_segundos:
            cod_str = str(int(float(str(cod_emp))))
            segundos_final = total_segundos * FATOR
            valor_excel = segundos_final / 86400.0 # Fração de dia para [h]:mm:ss
            
            writer.preencher_fiscal(cod_str, valor_excel)
            contador += 1
            
    logging.info(f"[FISCAL] Finalizado. {contador} empresas preenchidas na Master.")
    return True
