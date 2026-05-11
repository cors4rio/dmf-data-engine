import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()

q = """
    SELECT p.codi_emp, p.rfed_par, e.nome_emp
    FROM (
        SELECT codi_emp, rfed_par 
        FROM bethadba.efparametro_vigencia
    ) p
    JOIN bethadba.geempre e ON p.codi_emp = e.codi_emp
    WHERE p.rfed_par IN (7, 8)
"""
try:
    cursor.execute(q)
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print(f"Erro: {e}")
