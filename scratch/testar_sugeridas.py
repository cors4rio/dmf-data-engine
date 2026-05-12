from engine.database import db

def testar_sugeridas():
    tabelas = ["bethadba.FOFICHA", "bethadba.FOFUNC", "bethadba.foempregados"]
    for t in tabelas:
        print(f"\nTestando acesso a {t}...")
        try:
            # Pega o count para ver se a tabela 'existe'
            res = db.fetch_all(f"SELECT COUNT(*) as total FROM {t}")
            print(f"  [+] SUCESSO! Total de registros: {res[0]['total']}")
            
            # Pega as colunas se funcionar
            db.connect()
            cursor = db.conn.cursor()
            cursor.execute(f"SELECT * FROM {t} WHERE 1=0")
            colunas = [column[0] for column in cursor.description]
            print(f"  Colunas: {', '.join(colunas[:10])}...")
            
        except Exception as e:
            print(f"  [-] FALHA: {e}")

if __name__ == "__main__":
    testar_sugeridas()
