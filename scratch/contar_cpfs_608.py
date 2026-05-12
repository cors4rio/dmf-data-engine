from engine.database import db

def contar_cpfs():
    print("=== CONTAGEM DE CPFs ÚNICOS - EMPRESA 608 ===")
    
    # Buscando nome da coluna de CPF (geralmente num_cpf ou cpf)
    query = """
        SELECT 
            COUNT(DISTINCT f.cpf) as total_cpfs
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = 608
        AND f.admissao <= '2026-04-30'
        AND (r.demissao IS NULL OR r.demissao >= '2026-04-01')
    """
    
    try:
        res = db.fetch_all(query)
        print(f"Total de CPFs únicos: {res[0]['total_cpfs']}")
    except:
        # Tentar com num_cpf se cpf falhar
        res = db.fetch_all(query.replace("f.cpf", "f.num_cpf"))
        print(f"Total de CPFs únicos (num_cpf): {res[0]['total_cpfs']}")

if __name__ == "__main__":
    contar_cpfs()
