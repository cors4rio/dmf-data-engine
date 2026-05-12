import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("SELECT codi_acu, sum(vlor_mac) FROM bethadba.efmovacu where codi_emp=1445 and data_mac between '2026-04-01' and '2026-04-30' group by codi_acu")
rows = cursor.fetchall()
for row in rows:
    print(row)
