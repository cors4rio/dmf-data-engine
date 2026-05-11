import pyodbc

try:
    conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
    cursor=conn.cursor()
    cursor.execute("""
    SELECT l.codi_emp, SUM(DATEDIFF(second, 
        YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tini_log, 
        COALESCE(
            YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log, 
            YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log
        )
    )) 
    FROM bethadba.geloguser l 
    WHERE l.sist_log=5 AND l.tfim_log IS NOT NULL 
    AND l.codi_emp IN (1191, 1193) 
    AND l.data_log BETWEEN '2026-03-01' AND '2026-03-31' 
    GROUP BY l.codi_emp
    """)
    print("Result:", cursor.fetchall())
    conn.close()
except Exception as e:
    print("Error:", e)
