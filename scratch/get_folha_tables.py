from engine.database import db
import logging

logging.basicConfig(level=logging.INFO)

def buscar():
    print("=== BUSCANDO ESTRUTURA FOFICHA/FOFUNC ===")
    
    # 1. Localizar Tabelas
    query_tabs = """
        SELECT t.table_name, u.user_name as creator
        FROM systable t
        JOIN sysuser u ON t.creator = u.user_id
        WHERE (t.table_name LIKE 'foficha%' OR t.table_name LIKE 'fofunc%')
    """
    tabs = db.fetch_all(query_tabs)
    
    if not tabs:
        print("Nenhuma tabela encontrada com esses nomes.")
        return

    for t in tabs:
        full_name = f"{t['creator']}.{t['table_name']}"
        print(f"\n--- Estrutura de {full_name} ---")
        
        query_cols = f"""
            SELECT c.column_name, c.domain_name
            FROM syscolumn c
            JOIN systable t2 ON c.table_id = t2.table_id
            WHERE t2.table_name = '{t['table_name']}'
        """
        cols = db.fetch_all(query_cols)
        for c in cols:
            print(f"  {c['column_name']} ({c['domain_name']})")

if __name__ == "__main__":
    buscar()
