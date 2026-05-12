import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()

q = """
    SELECT rfed_par, COUNT(*) 
    FROM bethadba.efparametro_vigencia 
    GROUP BY rfed_par
    ORDER BY 2 DESC
"""
cursor.execute(q)
for row in cursor.fetchall():
    print(f"rfed_par: {row[0]}, Qtd: {row[1]}")
