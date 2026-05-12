from engine.database import db

def detalhar_filiais():
    print("=== RESUMO POR FILIAL - EMPRESA 608 ===")
    
    query = """
        SELECT 
            f.i_filiais,
            COUNT(*) as total
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = 608
        AND f.admissao <= '2026-04-30'
        AND (r.demissao IS NULL OR r.demissao >= '2026-04-01')
        GROUP BY f.i_filiais
        ORDER BY f.i_filiais
    """
    
    dados = db.fetch_all(query)
    for r in dados:
        print(f"  Filial {r['i_filiais']}: {r['total']} colaboradores")

if __name__ == "__main__":
    detalhar_filiais()
