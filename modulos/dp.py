import logging
import os
from engine.database import db
from engine.excel_parser import ExcelParser

def extrair_e_preencher_dp(writer, data_inicio, data_fim):
    """
    Módulo DP (Folha de Pagamento)
    - Extrai dados ativos do Domínio.
    - Faz a dupla checagem com a Planilha da Carol.
    - Se houver divergência, a planilha vence.
    - Calcula o tempo pela regra ((ativos * 0.33) + 1.5) e escreve na Coluna Q.
    """
    logging.info("[DP] Iniciando extração e cálculo de Folha...")
    
    # 1. Query no Domínio
    query = """
    SELECT
        e.codi_emp,
        SUM(CASE WHEN e.vinculo IN (1, 6, 11) THEN 1 ELSE 0 END) AS total_ativos
    FROM bethadba.foempregados e
    LEFT JOIN bethadba.forescisoes r
        ON r.codi_emp = e.codi_emp
       AND r.i_empregados = e.i_empregados
       AND r.demissao < ?
    WHERE e.admissao <= ?
      AND r.i_empregados IS NULL
    GROUP BY e.codi_emp
    """
    db_results = db.fetch_all(query, (data_inicio, data_fim))
    
    dados_dominio = {}
    if db_results:
        for row in db_results:
            cod_emp = row.get('codi_emp')
            if cod_emp:
                cod_str = str(int(float(str(cod_emp))))
                dados_dominio[cod_str] = int(row.get('total_ativos', 0))
    else:
        logging.warning("[DP] Nenhum dado retornado do Domínio.")
    
    # 2. Ler Planilha da Carol
    caminho_planilha = os.path.join("ENTRADAS_MANUAIS", "Controle de Empregados (CAROL).xls")
    dados_planilha = ExcelParser.ler_planilha_carol(caminho_planilha) or {}
    
    # 3. Consolidação e Dupla Checagem (Planilha Vence)
    # Pega a união de todas as chaves
    todas_chaves = set(dados_dominio.keys()).union(set(dados_planilha.keys()))
    
    # Exceções
    dp_nao = _ler_dp_nao()
    
    contador = 0
    for cod_str in todas_chaves:
        # Verifica se é Exceção Absoluta
        if cod_str in dp_nao:
            writer.preencher_dp(cod_str, dp_nao[cod_str]) # "DP NÃO" ou 1.5/24.0
            contador += 1
            continue
            
        tot_dom = dados_dominio.get(cod_str, 0)
        tot_pla = dados_planilha.get(cod_str, {}).get('total_ativos', -1)
        
        # Dupla checagem
        total_final = tot_dom
        if tot_pla != -1 and tot_pla != tot_dom:
            logging.info(f"[DP] Divergência no cliente {cod_str}: DB={tot_dom}, Planilha={tot_pla}. Planilha vence.")
            total_final = tot_pla
            
        # 4. Cálculo
        MINIMO = (5.0 / 60.0) / 24.0 # 5 minutos
        if total_final > 0:
            horas = (total_final * 0.33) + 1.5
            valor_excel = horas / 24.0
        else:
            valor_excel = MINIMO
            
        writer.preencher_dp(cod_str, valor_excel)
        contador += 1
        
    logging.info(f"[DP] Concluído. {contador} empresas calculadas e preenchidas na Master.")
    return True

def _ler_dp_nao():
    """Lê a lista de exceções do DP NÃO."""
    arquivo = os.path.join("config", "nao_faz_setor", "DP NAO.txt")
    excecoes = {}
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or "Não entra" in linha: continue
                # Formatos aceitos: '123 NOME' ou '123;NOME'
                partes = linha.replace(';', ' ').replace('\t', ' ').split(' ', 1)
                try:
                    cod_str = str(int(float(partes[0])))
                    if "1:30" in linha:
                        excecoes[cod_str] = 1.5 / 24.0 # Float do excel para consultoria
                    else:
                        excecoes[cod_str] = "DP NÃO"
                except Exception:
                    continue
    return excecoes
