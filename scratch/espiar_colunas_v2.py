from engine.database import db

def espiar():
    query = "SELECT * FROM bethadba.foempregados WHERE 1=0"
    try:
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute(query)
        colunas = [column[0] for column in cursor.description]
        print("As primeiras 20 colunas da foempregados:")
        for col in colunas[:20]:
            print(f"  - {col}")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    espiar()
