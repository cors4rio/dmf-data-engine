import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()

data_fim_mes = '2025-02-28' # Usando fevereiro como exemplo do usuario

q = f"""
    SELECT 
        COALESCE(p.codi_emp, s.codi_emp) as codi_emp, 
        p.rfed_par, 
        s.forma_tributacao
    FROM (
        SELECT codi_emp, rfed_par
        FROM bethadba.efparametro_vigencia t
        INNER JOIN (
            SELECT codi_emp as c_emp, MAX(vigencia_par) as max_v
            FROM bethadba.efparametro_vigencia
            WHERE vigencia_par <= '{data_fim_mes}'
            GROUP BY codi_emp
        ) ult ON t.codi_emp = ult.c_emp AND t.vigencia_par = ult.max_v
    ) p
    FULL OUTER JOIN (
        SELECT codi_emp, forma_tributacao
        FROM bethadba.ctparmto_sped_vigencia t
        INNER JOIN (
            SELECT codi_emp as c_emp, MAX(vigencia) as max_v
            FROM bethadba.ctparmto_sped_vigencia
            WHERE vigencia <= '{data_fim_mes}'
            GROUP BY codi_emp
        ) ult ON t.codi_emp = ult.c_emp AND t.vigencia = ult.max_v
    ) s ON p.codi_emp = s.codi_emp
    WHERE COALESCE(p.codi_emp, s.codi_emp) = 1227
"""

cursor.execute(q)
row = cursor.fetchone()
print(f"Empresa 1227 - rfed_par: {row[1]}, forma_tributacao: {row[2]}")
