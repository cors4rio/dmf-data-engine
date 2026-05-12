from engine.database import db
import logging

logging.basicConfig(level=logging.INFO)

def localizar_tabelas():
    print("=== BUSCA DE TABELAS DP (DOMÍNIO) ===")
    
    # Query para listar todas as tabelas do usuário BETHADBA
    query = """
        SELECT table_name 
        FROM systable 
        WHERE creator = (SELECT user_id FROM sysuser WHERE user_name = 'BETHADBA')
        AND (table_name LIKE 'FO%' OR table_name LIKE '%EMP%')
        ORDER BY table_name
    """
    
    tabelas = db.fetch_all(query)
    if tabelas:
        print(f"Encontradas {len(tabelas)} tabelas candidatas:")
        for t in tabelas:
            print(f"  - {t['table_name']}")
    else:
        print("Nenhuma tabela encontrada com esses critérios.")

if __name__ == "__main__":
    localizar_tabelas()
