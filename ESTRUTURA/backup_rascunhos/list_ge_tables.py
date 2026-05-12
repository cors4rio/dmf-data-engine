import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()

# Lista todas as tabelas do bethadba que começam com "ge"
cursor.execute("SELECT table_name FROM SYS.SYSTABLE WHERE table_name LIKE 'ge%' AND creator = (SELECT user_id FROM SYS.SYSUSER WHERE user_name = 'bethadba')")
for row in cursor.fetchall():
    print(row[0])
