from engine.database import db

def analisar_833():
    print("=== ANÁLISE EMPRESA 833 (BASE MÊS 04) ===")
    
    # 1. Total de registros na foempregados para 833
    query_emp = "SELECT COUNT(*) as total FROM bethadba.foempregados WHERE codi_emp = 833"
    res_emp = db.fetch_all(query_emp)
    print(f"Total de empregados (base histórica completa) na 833: {res_emp[0]['total']}")
    
    # 2. Investigar a tabela de rescisões (para saber quem saiu)
    try:
        # Primeiro espiar colunas de forescisoes
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM bethadba.forescisoes WHERE 1=0")
        cols_resc = [column[0] for column in cursor.description]
        print(f"Colunas de forescisoes: {', '.join(cols_resc[:10])}...")
        
        # Contar rescisões na 833
        query_resc = "SELECT COUNT(*) as total FROM bethadba.forescisoes WHERE codi_emp = 833"
        res_resc = db.fetch_all(query_resc)
        print(f"Total de rescisões registradas na 833: {res_resc[0]['total']}")
        
    except Exception as e:
        print(f"Erro ao acessar rescisões: {e}")

if __name__ == "__main__":
    analisar_833()
