import logging
import os
from engine.excel_parser import ExcelParser

def extrair_e_preencher_contabil(writer):
    """
    Lê os totais da planilha HORAS CONTABEIS.xlsx (já gerada por outro projeto)
    e integra na Planilha Master (Coluna P).
    """
    caminho = os.path.join("ENTRADAS_MANUAIS", "HORAS CONTABEIS.xlsx")
    
    logging.info("[CONTÁBIL] Iniciando integração da planilha de horas Contábeis...")
    dados = ExcelParser.ler_pre_planilha_contabil(caminho)
    
    if not dados:
        logging.warning("[CONTÁBIL] Falha ou planilha inexistente. Pulando integração.")
        return False
        
    contador = 0
    for cod_str, total_horas in dados.items():
        # Apenas joga o valor float (fração de dia)
        if isinstance(total_horas, float):
            writer.preencher_contabil(cod_str, total_horas)
            contador += 1
            
    logging.info(f"[CONTÁBIL] Integração concluída. {contador} empresas atualizadas na Master.")
    return True
