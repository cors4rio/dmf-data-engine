from engine.database import db

def listar():
    query = """
        SELECT t.table_name 
        FROM systable t
        JOIN sysuser u ON t.creator = u.user_id
        WHERE u.user_name = 'BETHADBA'
        ORDER BY t.table_name
    """
    res = db.fetch_all(query)
    with open("scratch/lista_objetos_bethadba.txt", "w") as f:
        for r in res:
            f.write(r['table_name'] + "\n")
    print(f"Salvas {len(res)} tabelas em scratch/lista_objetos_bethadba.txt")

if __name__ == "__main__":
    listar()
