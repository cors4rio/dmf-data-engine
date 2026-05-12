from engine.database import db

def contar_contribuintes(codi_emp, mes_referencia):
    print(f"=== CONTAGEM CONTRIBUINTES - EMPRESA {codi_emp} - REF: {mes_referencia} ===")
    
    # Query para FOCONTRIBUINTES (Sócios/Autônomos)
    # i_situacao ou similar costuma ser o status. 
    # Vou primeiro espiar colunas para garantir.
    try:
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM bethadba.FOCONTRIBUINTES WHERE 1=0")
        cols = [column[0] for column in cursor.description]
        print(f"Colunas FOCONTRIBUINTES: {', '.join(cols[:15])}...")
        
        # Tentando contar ativos (geralmente situacao 1 ou data_rescisao nula)
        query = f"""
            SELECT COUNT(*) as total 
            FROM bethadba.FOCONTRIBUINTES 
            WHERE codi_emp = {codi_emp}
            AND admissao <= '{mes_referencia}'
            AND (rescisao IS NULL OR rescisao > '{mes_referencia}')
        """
        res = db.fetch_all(query)
        print(f"Total de Contribuintes Ativos: {res[0]['total']}")
        
        # Listar nomes para conferência
        nomes = db.fetch_all(f"SELECT nome FROM bethadba.FOCONTRIBUINTES WHERE codi_emp = {codi_emp} AND admissao <= '{mes_referencia}' AND (rescisao IS NULL OR rescisao > '{mes_referencia}')")
        for n in nomes:
            print(f"  - [CONTRIBUINTE] {n['nome']}")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    contar_contribuintes(833, '2026-04-30')
