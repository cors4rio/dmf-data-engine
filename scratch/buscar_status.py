from engine.database import db

def buscar_status():
    query = "SELECT * FROM bethadba.foempregados WHERE 1=0"
    try:
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute(query)
        colunas = [column[0] for column in cursor.description]
        print("Candidatos a campo de Status/Situação:")
        for col in colunas:
            if "SIT" in col.upper() or "ATIV" in col.upper() or "STATUS" in col.upper():
                print(f"  - {col}")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    buscar_status()
