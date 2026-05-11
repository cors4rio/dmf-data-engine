import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("SELECT cfps_sai, sum(vcon_sai) FROM bethadba.efsaidas where codi_emp=1445 and dsai_sai between '2026-04-01' and '2026-04-30' group by cfps_sai")
rows = cursor.fetchall()
for row in rows:
    print(row)
