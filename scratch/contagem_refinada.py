from engine.database import db

def contar_mes_base(codi_emp, mes_referencia):
    # mes_referencia formato 'YYYY-MM-DD' (último dia do mês)
    print(f"=== CONTAGEM REFINADA - EMPRESA {codi_emp} - REF: {mes_referencia} ===")
    
    query = f"""
        SELECT 
            f.i_empregados,
            f.nome,
            f.admissao,
            r.demissao
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = {codi_emp}
        AND f.admissao <= '{mes_referencia}'
        AND (r.demissao IS NULL OR r.demissao > '{mes_referencia}')
        ORDER BY f.nome
    """
    
    dados = db.fetch_all(query)
    for r in dados:
        print(f"  [{r['i_empregados']}] {r['nome']} - Adm: {r['admissao']} | Dem: {r['demissao'] or 'Ativo'}")
    
    print(f"\nTotal para o Mês {mes_referencia[5:7]}: {len(dados)}")

if __name__ == "__main__":
    contar_mes_base(833, '2026-04-30')
