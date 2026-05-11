import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("""
SELECT 
    sum(s.vcon_sai) as vcon,
    sum(s.vprod_sai) as vprod,
    sum(s.vdesace_sai) as vdes,
    sum(s.valor_bc_icms_st_sai) as vbc_st
FROM bethadba.efsaidas s
WHERE s.codi_emp=1445 and s.dsai_sai between '2026-04-01' and '2026-04-30'
  and s.situacao_sai <> 9
""")
print([c[0] for c in cursor.description])
print(cursor.fetchall())
