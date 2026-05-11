import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
cursor.execute("SELECT top 10 codi_emp, data_mac, codi_acu, sum(vlor_mac) FROM bethadba.efmovacu group by codi_emp, data_mac, codi_acu order by data_mac desc")
rows = cursor.fetchall()
for row in rows:
    print(row)
