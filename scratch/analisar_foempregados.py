from engine.database import db

def analisar_colunas():
    # Buscando colunas da tabela foempregados
    # Usando sys.syscolumn para evitar erro de domain_name
    query = """
        SELECT c.column_name
        FROM syscolumn c
        JOIN systable t ON c.table_id = t.table_id
        WHERE t.table_name = 'foempregados'
        ORDER BY c.column_id
    """
    res = db.fetch_all(query)
    print("Colunas de foempregados:")
    for r in res:
        print(f"  - {r['column_name']}")

if __name__ == "__main__":
    analisar_colunas()
