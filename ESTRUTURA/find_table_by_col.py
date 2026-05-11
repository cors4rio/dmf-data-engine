import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()

q = """
    SELECT t.table_name
    FROM SYS.SYSTABLE t
    JOIN SYS.SYSCOLUMN c ON t.table_id = c.table_id
    WHERE c.column_name = 'nome_emp'
    AND t.creator = (SELECT user_id FROM SYS.SYSUSER WHERE user_name = 'bethadba')
"""
try:
    cursor.execute(q)
    for row in cursor.fetchall():
        print(row[0])
except Exception as e:
    print(f"Erro: {e}")
