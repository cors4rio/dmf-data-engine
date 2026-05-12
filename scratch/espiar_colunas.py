from engine.database import db

def espiar():
    # Query que não traz dados, mas traz os nomes das colunas
    query = "SELECT * FROM bethadba.foempregados WHERE 1=0"
    try:
        # Usando o cursor diretamente para pegar a descrição das colunas
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute(query)
        colunas = [column[0] for column in cursor.description]
        print("Colunas reais da foempregados:")
        for col in colunas:
            print(f"  - {col}")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    espiar()
