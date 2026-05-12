import pyodbc

xls_path = r'C:\Users\DMF-AUTOMACAO\Downloads\Relação de Regime de Empresa 022026s.xls'
db_conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'

def get_db_data(cod_list):
    conn = pyodbc.connect(db_conn_str)
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(cod_list))
    q = f"""
        SELECT 
            COALESCE(p.codi_emp, s.codi_emp) as codi_emp, 
            p.rfed_par, 
            s.forma_tributacao
        FROM (
            SELECT t.codi_emp, t.rfed_par
            FROM bethadba.efparametro_vigencia t
            INNER JOIN (
                SELECT codi_emp as c_emp, MAX(vigencia_par) as max_v
                FROM bethadba.efparametro_vigencia
                WHERE vigencia_par <= '2025-12-31'
                GROUP BY codi_emp
            ) ult ON t.codi_emp = ult.c_emp AND t.vigencia_par = ult.max_v
        ) p
        FULL OUTER JOIN (
            SELECT t.codi_emp, t.forma_tributacao
            FROM bethadba.ctparmto_sped_vigencia t
            INNER JOIN (
                SELECT codi_emp as c_emp, MAX(vigencia) as max_v
                FROM bethadba.ctparmto_sped_vigencia
                WHERE vigencia <= '2025-12-31'
                GROUP BY codi_emp
            ) ult ON t.codi_emp = ult.c_emp AND t.vigencia = ult.max_v
        ) s ON p.codi_emp = s.codi_emp
        WHERE COALESCE(p.codi_emp, s.codi_emp) IN ({placeholders})
    """
    cursor.execute(q, cod_list)
    return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

conn_str = r'DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};DBQ=' + xls_path + ';ReadOnly=1'
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()
tables = [t.table_name for t in cursor.tables()]
cursor.execute(f'SELECT * FROM [{tables[0]}]')

imunes_isentas = []
for row in cursor.fetchall():
    s_row = str(row)
    if "Imune" in s_row or "Isenta" in s_row:
        try:
            cod = int(str(row[0]))
            imunes_isentas.append((cod, s_row))
        except:
            continue

if imunes_isentas:
    print(f"Encontradas {len(imunes_isentas)} empresas Imunes/Isentas.")
    cods = [x[0] for x in imunes_isentas]
    db_data = get_db_data(cods)
    for cod, row_str in imunes_isentas[:20]:
        db_v = db_data.get(cod, ("?", "?"))
        print(f"Cod: {cod} | DB (rfed, sped): {db_v} | Row: {row_str[:100]}...")
else:
    print("Nenhuma empresa Imune ou Isenta encontrada nas primeiras linhas.")
