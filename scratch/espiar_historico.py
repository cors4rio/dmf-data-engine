from engine.database import db

def espiar_historico():
    query = "SELECT * FROM bethadba.fohistempregados WHERE 1=0"
    try:
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute(query)
        colunas = [column[0] for column in cursor.description]
        print("Colunas da fohistempregados:")
        for col in colunas:
            print(f"  - {col}")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    espiar_historico()
