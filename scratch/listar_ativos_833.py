from engine.database import db

def listar_ativos_833():
    print("=== FUNCIONÁRIOS ATIVOS - EMPRESA 833 ===")
    
    # Query para pegar quem NÃO está na tabela de rescisões
    query = """
        SELECT 
            f.i_empregados,
            f.nome,
            f.admissao
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = 833
        AND r.i_empregados IS NULL
        ORDER BY f.nome
    """
    
    dados = db.fetch_all(query)
    for r in dados:
        print(f"  [{r['i_empregados']}] {r['nome']} - Adm: {r['admissao']}")
    
    print(f"\nTotal calculado: {len(dados)}")

if __name__ == "__main__":
    listar_ativos_833()
