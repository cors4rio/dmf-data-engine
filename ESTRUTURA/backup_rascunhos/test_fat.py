import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("SELECT situacao_sai, cancelada_sai, sum(vcon_sai) FROM bethadba.efsaidas where codi_emp=1445 and dsai_sai between '2026-04-01' and '2026-04-30' group by situacao_sai, cancelada_sai")
print("Saidas:", cursor.fetchall())

cursor.execute("SELECT situacao_ser, cancelada_ser, sum(vcon_ser) FROM bethadba.efservicos where codi_emp=1445 and dser_ser between '2026-04-01' and '2026-04-30' group by situacao_ser, cancelada_ser")
print("Servicos:", cursor.fetchall())
