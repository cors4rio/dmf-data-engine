import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("""
SELECT 
    sum(s.vexc_sai) as vexc,
    sum(s.vfre_sai) as frete,
    sum(s.vseg_sai) as seg,
    sum(s.vdesace_sai) as des,
    sum(s.valor_bc_icms_st_sai) as bc_st
FROM bethadba.efsaidas s
WHERE s.codi_emp=1445 and s.dsai_sai between '2026-04-01' and '2026-04-30'
  and s.situacao_sai <> 9
""")
print(cursor.fetchall())
