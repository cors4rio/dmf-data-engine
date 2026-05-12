import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("""
SELECT n.cfop_nat, sum(s.vcon_sai) 
FROM bethadba.efsaidas s
JOIN bethadba.efnatureza n ON s.codi_nat = n.codi_nat
WHERE s.codi_emp=1445 and s.dsai_sai between '2026-04-01' and '2026-04-30'
GROUP BY n.cfop_nat
""")
rows = cursor.fetchall()
for row in rows:
    print(row)
