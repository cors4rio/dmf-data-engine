from engine.database import db

def detalhar_608():
    print("=== DETALHAMENTO CATEGORIAS - EMPRESA 608 ===")
    
    query = """
        SELECT 
            f.i_empregados,
            f.nome,
            f.categoria,
            f.admissao,
            r.demissao
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = 608
        AND f.admissao <= '2026-04-30'
        AND (r.demissao IS NULL OR r.demissao >= '2026-04-01')
        ORDER BY f.categoria, f.nome
    """
    
    dados = db.fetch_all(query)
    for r in dados:
        print(f"  Cat: {r['categoria']} | {r['nome'][:30]:<30} | Adm: {r['admissao']}")
    
    # Resumo por categoria
    categorias = {}
    for r in dados:
        cat = r['categoria']
        categorias[cat] = categorias.get(cat, 0) + 1
    
    print("\nResumo por Categoria:")
    for cat, total in categorias.items():
        print(f"  Categoria {cat}: {total} pessoas")

if __name__ == "__main__":
    detalhar_608()
