import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("SELECT * FROM bethadba.efmovacu where codi_emp=1445 and data_acu between '2026-04-01' and '2026-04-30'")
print([column[0] for column in cursor.description])
rows = cursor.fetchall()
for row in rows:
    print(row)
