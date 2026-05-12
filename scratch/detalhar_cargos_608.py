from engine.database import db

def detalhar_cargos_deptos():
    print("=== DETALHAMENTO CARGOS/DEPTOS - EMPRESA 608 ===")
    
    query = """
        SELECT 
            f.i_empregados,
            f.nome,
            f.i_cargos,
            f.i_depto,
            f.admissao
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = 608
        AND f.admissao <= '2026-04-30'
        AND (r.demissao IS NULL OR r.demissao >= '2026-04-01')
        ORDER BY f.i_cargos, f.i_depto
    """
    
    dados = db.fetch_all(query)
    for r in dados:
        print(f"  Cargo: {r['i_cargos']} | Depto: {r['i_depto']} | {r['nome'][:20]} | Adm: {r['admissao']}")

if __name__ == "__main__":
    detalhar_cargos_deptos()
