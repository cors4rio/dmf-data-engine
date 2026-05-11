import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("""
SELECT *
FROM bethadba.efsaidas
WHERE codi_emp=1445 and dsai_sai between '2026-04-01' and '2026-04-30'
  and vcon_sai = 1151.20
""")
print(cursor.fetchall())
