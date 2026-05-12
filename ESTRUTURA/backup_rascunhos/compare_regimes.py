import pyodbc

xls_path = r'C:\Users\DMF-AUTOMACAO\Downloads\Relação de Regime de Empresa 022026s.xls'
db_conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'

def get_xls_data():
    conn_str = r'DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};DBQ=' + xls_path + ';ReadOnly=1'
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    tables = [t.table_name for t in cursor.tables()]
    cursor.execute(f'SELECT * FROM [{tables[0]}]')
    data = []
    for row in cursor.fetchall():
        try:
            cod = int(str(row[0]))
            # Procura o regime nas colunas (geralmente entre 3 e 6)
            regime = "N/A"
            for cell in row[1:7]:
                s_cell = str(cell)
                if any(x in s_cell for x in ["Lucro", "Simples", "Imune", "Isenta", "Microempresa"]):
                    regime = s_cell
                    break
            data.append((cod, regime, row))
        except:
            continue
    return data

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

xls_data = get_xls_data()
cods = [x[0] for x in xls_data[:100]] # Pega 100 primeiras
db_results = get_db_data(cods)

print(f"{'Cod':<6} | {'XLS Regime':<20} | {'rfed':<5} | {'sped':<5}")
print("-" * 60)
for cod, regime, full_row in xls_data[:100]:
    db_vals = db_results.get(cod, (None, None))
    rfed = db_vals[0] if db_vals[0] is not None else "?"
    sped = db_vals[1] if db_vals[1] is not None else "?"
    print(f"{cod:<6} | {regime:<20} | {rfed:<5} | {sped:<5}")

# Caso específico 1227
db_1227 = get_db_data([1227]).get(1227, ("?", "?"))
print(f"\nREVISAO 1227: rfed={db_1227[0]}, sped={db_1227[1]}")
