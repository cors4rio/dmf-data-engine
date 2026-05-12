from engine.database import db

def contar_movimentacao_mes(codi_emp, mes, ano):
    import calendar
    last_day = calendar.monthrange(ano, mes)[1]
    data_inicio = f"{ano}-{mes:02d}-01"
    data_fim = f"{ano}-{mes:02d}-{last_day}"
    
    print(f"=== RELATÓRIO CAROL (BANCO) - EMPRESA {codi_emp} - REF: {mes:02d}/{ano} ===")
    
    # Lógica: 
    # 1. Admissão deve ser até o fim do mês
    # 2. Demissão deve ser NULA ou a partir do primeiro dia do mês
    query = f"""
        SELECT 
            f.i_empregados,
            f.nome,
            f.admissao,
            r.demissao
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = {codi_emp}
        AND f.admissao <= '{data_fim}'
        AND (r.demissao IS NULL OR r.demissao >= '{data_inicio}')
        ORDER BY f.nome
    """
    
    dados = db.fetch_all(query)
    for r in dados:
        status = "ATIVO" if not r['demissao'] else f"DEMITIDO EM {r['demissao']}"
        print(f"  - {r['nome'][:30]:<30} | Adm: {r['admissao']} | {status}")
    
    print(f"\nTOTAL DE COLABORADORES NO MÊS: {len(dados)}")

if __name__ == "__main__":
    contar_movimentacao_mes(833, 4, 2026)
