from engine.database import db

def buscar_outros_trabalhadores(codi_emp, mes_referencia):
    print(f"=== BUSCANDO SÓCIOS/AUTÔNOMOS - EMPRESA {codi_emp} ===")
    
    # 1. Testar Sócios
    try:
        query_socios = f"""
            SELECT nome, admissao FROM bethadba.fosocios 
            WHERE codi_emp = {codi_emp} 
            AND admissao <= '{mes_referencia}'
        """
        socios = db.fetch_all(query_socios)
        print(f"Sócios encontrados: {len(socios)}")
        for s in socios:
            print(f"  - [SÓCIO] {s['nome']} (Adm: {s['admissao']})")
    except Exception as e:
        print(f"Erro ao buscar sócios: {e}")

    # 2. Testar Autônomos
    try:
        query_auton = f"""
            SELECT nome, admissao FROM bethadba.foautonomos 
            WHERE codi_emp = {codi_emp}
            AND admissao <= '{mes_referencia}'
        """
        auton = db.fetch_all(query_auton)
        print(f"Autônomos encontrados: {len(auton)}")
        for a in auton:
            print(f"  - [AUTÔNOMO] {a['nome']} (Adm: {a['admissao']})")
    except Exception as e:
        print(f"Erro ao buscar autônomos: {e}")

if __name__ == "__main__":
    buscar_outros_trabalhadores(833, '2026-04-30')
