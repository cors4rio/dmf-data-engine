import logging
import os
from engine.database import db
from engine.excel_parser import ExcelParser

def extrair_e_preencher_dp(writer, data_inicio, data_fim, fator_carga=0.33, overhead_fixo=1.5, tempo_minimo_minutos=5.0, consultoria_horas=1.5, tempo_fixo_apenas_socios=1.0, caminho_carol=None):
    """
    Módulo DP (Folha de Pagamento)
    - Extrai dados segregados do Domínio (Funcionários=1, Estagiários=6, Sócios=11).
    - Faz a dupla checagem com a Planilha da Carol. Planilha vence no total.
    - Aplica as regras de negócio setoriais de precificação em cascata.
    """
    logging.info(f"[DP] Iniciando Folha com tempo_colaborador={fator_carga}h, fixo_empresa={overhead_fixo}h, fixo_socios={tempo_fixo_apenas_socios}h...")
    
    # 1. Query no Domínio com breakdown por tipo de vínculo
    query = """
    SELECT
        e.codi_emp,
        SUM(CASE WHEN e.vinculo = 1 THEN 1 ELSE 0 END) AS qtd_func,
        SUM(CASE WHEN e.vinculo = 6 THEN 1 ELSE 0 END) AS qtd_estag,
        SUM(CASE WHEN e.vinculo = 11 THEN 1 ELSE 0 END) AS qtd_contrib,
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
                dados_dominio[cod_str] = {
                    'func': int(row.get('qtd_func', 0)),
                    'estag': int(row.get('qtd_estag', 0)),
                    'contrib': int(row.get('qtd_contrib', 0)),
                    'total_ativos': int(row.get('total_ativos', 0))
                }
    else:
        logging.warning("[DP] Nenhum dado retornado do Domínio.")
    
    # 2. Ler Planilha da Carol (caminho explícito sobrescreve fallback local)
    _svc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho_planilha = caminho_carol or os.path.join(_svc, "ENTRADAS_MANUAIS", "Controle de Empregados (CAROL).xls")
    dados_planilha = ExcelParser.ler_planilha_carol(caminho_planilha) or {}
    
    # 3. Consolidação e Dupla Checagem (Planilha Vence)
    todas_chaves = set(dados_dominio.keys()).union(set(dados_planilha.keys()))
    
    # Exceções
    dp_nao = _ler_dp_nao(consultoria_horas=consultoria_horas)
    
    contador = 0
    for cod_str in todas_chaves:
        # Verifica se é Exceção Absoluta
        if cod_str in dp_nao:
            writer.preencher_dp(cod_str, dp_nao[cod_str])
            contador += 1
            continue
            
        dom_obj = dados_dominio.get(cod_str, {'func': 0, 'estag': 0, 'contrib': 0, 'total_ativos': 0})
        pla_obj = dados_planilha.get(cod_str, None)
        
        # Dupla checagem
        final_func = dom_obj['func']
        final_estag = dom_obj['estag']
        final_contrib = dom_obj['contrib']
        final_total = dom_obj['total_ativos']
        
        if pla_obj and pla_obj['total_ativos'] != dom_obj['total_ativos']:
            logging.info(f"[DP] Divergência no cliente {cod_str}: DB={dom_obj['total_ativos']}, Planilha={pla_obj['total_ativos']}. Planilha vence.")
            final_func = pla_obj.get('func', 0)
            final_estag = pla_obj.get('estag', 0)
            final_contrib = pla_obj.get('contrib', 0)
            final_total = pla_obj['total_ativos']
            
        # 4. Aplicação das Regras Setoriais em Cascata
        MINIMO = (float(tempo_minimo_minutos) / 60.0) / 24.0
        
        if final_total == 0:
            # Sem colaboradores ou movimentação
            valor_excel = MINIMO
        elif final_func == 0 and final_estag == 0 and final_contrib > 0:
            # Empresas com apenas sócios (contribuintes): conta o mesmo valor de exatamente 1 colaborador na fórmula
            horas = (1.0 * float(fator_carga)) + float(overhead_fixo)
            valor_excel = horas / 24.0
        else:
            # Possui funcionário ou estagiário: aplica a fórmula pelo total real de ativos
            horas = (final_total * float(fator_carga)) + float(overhead_fixo)
            valor_excel = horas / 24.0
            
        writer.preencher_dp(cod_str, valor_excel)
        contador += 1
        
    logging.info(f"[DP] Concluído. {contador} empresas calculadas e preenchidas na Master.")
    return True

def _ler_dp_nao(consultoria_horas=1.5):
    """Lê a lista de exceções do DP NÃO."""
    from modulos.excecoes import caminho_excecao
    arquivo = caminho_excecao("dp")
    excecoes = {}
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or "Não entra" in linha: continue
                partes = linha.replace(';', ' ').replace('\t', ' ').split(' ', 1)
                try:
                    cod_str = str(int(float(partes[0])))
                    if "1:30" in linha:
                        excecoes[cod_str] = float(consultoria_horas) / 24.0
                    else:
                        excecoes[cod_str] = "DP NÃO"
                except Exception:
                    continue
    return excecoes
