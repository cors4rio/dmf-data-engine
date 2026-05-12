import pyodbc
import json

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        query = "SELECT table_name FROM SYS.SYSTABLE WHERE creator = (SELECT user_id FROM SYS.SYSUSER WHERE user_name = 'bethadba')"
        cursor.execute(query)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        keywords = ['tempo', 'gasto', 'tarefa', 'ativid', 'desem', 'hora', 'cliente', 'usuari', 'colabor', 'empregado']
        res = [t for t in tables if any(kw in t.lower() for kw in keywords)]
        
        with open('ESTRUTURA/tables_found.txt', 'w', encoding='utf-8') as f:
            for r in res:
                f.write(r + '\n')
        print("Salvo em ESTRUTURA/tables_found.txt")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
