import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()

# Busca todas as tabelas
cursor.execute("SELECT table_name FROM SYS.SYSTABLE WHERE creator = (SELECT user_id FROM SYS.SYSUSER WHERE user_name = 'bethadba')")
tables = [row[0] for row in cursor.fetchall()]

keywords = ["fed", "regime", "param", "tribu", "imune", "isenta"]
matching_tables = [t for t in tables if any(kw in t.lower() for kw in keywords)]

print("Tabelas candidatas encontradas:")
for t in sorted(matching_tables):
    print(f"- {t}")
