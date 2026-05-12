from engine.database import db
import pyodbc
import logging

logging.basicConfig(level=logging.INFO)

def testar_conexoes():
    print("=== TESTE DE CREDENCIAIS (EXTERNO) ===")
    
    variacoes = [
        {"desc": "DSN Puro (Pode usar senha gravada)", "conn": "DSN=Contabil"},
        {"desc": "EXTERNO / EXTERNO (Maiúsculo)", "conn": "DSN=Contabil;UID=EXTERNO;PWD=EXTERNO"},
        {"desc": "externo / externo (Minúsculo)", "conn": "DSN=Contabil;UID=externo;PWD=externo"},
    ]
    
    for v in variacoes:
        print(f"\nTentando: {v['desc']}")
        try:
            conn = pyodbc.connect(v['conn'], timeout=5)
            print(f"  [+] SUCESSO!")
            conn.close()
            return v['conn'] # Retorna a que funcionou
        except Exception as e:
            print(f"  [-] FALHA: {e}")
    
    return None

if __name__ == "__main__":
    testar_conexoes()
