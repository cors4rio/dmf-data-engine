from engine.database import db

def analisar_sindicatos():
    print("=== RESUMO POR SINDICATO - EMPRESA 608 ===")
    
    query = """
        SELECT 
            f.i_sindicatos_cadastro,
            COUNT(*) as total
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = 608
        AND f.admissao <= '2026-04-30'
        AND (r.demissao IS NULL OR r.demissao >= '2026-04-01')
        GROUP BY f.i_sindicatos_cadastro
        ORDER BY f.i_sindicatos_cadastro
    """
    
    dados = db.fetch_all(query)
    for r in dados:
        print(f"  Sindicato {r['i_sindicatos_cadastro']}: {r['total']} colaboradores")

if __name__ == "__main__":
    analisar_sindicatos()
