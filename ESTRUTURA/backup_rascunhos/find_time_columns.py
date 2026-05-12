import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        with open('ESTRUTURA/time_columns.txt', 'w', encoding='utf-8') as f:
            query = """
            SELECT t.table_name, c.column_name 
            FROM SYS.SYSTABLE t
            JOIN SYS.SYSCOLUMN c ON t.table_id = c.table_id
            WHERE t.creator = (SELECT user_id FROM SYS.SYSUSER WHERE user_name = 'bethadba')
              AND (
                  LOWER(c.column_name) LIKE '%tempo%' OR 
                  LOWER(c.column_name) LIKE '%gasto%' OR 
                  LOWER(c.column_name) LIKE '%hora%' OR 
                  LOWER(c.column_name) LIKE '%minuto%'
              )
            ORDER BY t.table_name, c.column_name
            """
            cursor.execute(query)
            cols = cursor.fetchall()
            
            f.write(f"Found {len(cols)} matching columns.\n\n")
            current_table = ""
            for row in cols:
                tname = row[0]
                cname = row[1]
                if tname != current_table:
                    # check if table has rows
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM bethadba.{tname}")
                        count = cursor.fetchone()[0]
                        f.write(f"\n--- {tname} ({count} rows) ---\n")
                    except Exception as e:
                        f.write(f"\n--- {tname} (Erro ao contar) ---\n")
                    current_table = tname
                f.write(f"  {cname}\n")
                    
        print("Salvo em ESTRUTURA/time_columns.txt")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
