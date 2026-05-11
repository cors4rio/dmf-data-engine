import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("SELECT top 10 * FROM bethadba.eftabela_cfps")
print([c[0] for c in cursor.description])
rows = cursor.fetchall()
for row in rows:
    print(row)
