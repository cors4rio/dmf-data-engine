from engine.database import db
import logging

logging.basicConfig(level=logging.INFO)

def diagnostico():
    print("=== DIAGNÓSTICO TABELAS DP (DOMÍNIO) - MODO 32-BIT ===")
    
    # Voltando a usar o DSN padrão, agora que estamos no Python correto
    print(f"Usando DSN padrão: {db.connection_string}")
    
    # Tabelas para investigar baseadas no mapeamento
    tabelas = ["FOFICHA", "FOFUNC", "FOEMPREGADOS", "FORESCISOES"]
    
    for tab in tabelas:
        print(f"\n--- Investigando: BETHADBA.{tab} ---")
        try:
            # Query para listar colunas no SQL Anywhere
            query_colunas = f"""
                SELECT c.column_name, c.domain_name, c.width, c.nulls
                FROM syscolumn c
                JOIN systable t ON c.table_id = t.table_id
                WHERE t.table_name = '{tab.lower()}' 
                   OR t.table_name = '{tab.upper()}'
            """
            colunas = db.fetch_all(query_colunas)
            if colunas:
                for col in colunas:
                    print(f"  > {col['column_name']} ({col['domain_name']})")
            else:
                print(f"  [!] Tabela {tab} não encontrada ou sem colunas acessíveis.")
        except Exception as e:
            print(f"  [!] Erro ao acessar {tab}: {e}")

    # Teste de contagem simples se as tabelas existirem
    print("\n--- Teste de Contagem (Exemplo) ---")
    query_teste = "SELECT COUNT(*) as total FROM BETHADBA.FOFICHA"
    res = db.fetch_all(query_teste)
    if res:
        print(f"Total na FOFICHA: {res[0]['total']}")
    else:
        print("Falha na contagem.")

if __name__ == "__main__":
    diagnostico()
