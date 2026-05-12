import pyodbc

xls_path = r'C:\Users\DMF-AUTOMACAO\Downloads\Relação de Regime de Empresa 022026s.xls'
db_conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'

def get_xls_map():
    conn_str = r'DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};DBQ=' + xls_path + ';ReadOnly=1'
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    tables = [t.table_name for t in cursor.tables()]
    cursor.execute(f'SELECT * FROM [{tables[0]}]')
    
    mapping = {}
    keywords = ["Lucro Presumido", "Lucro Real", "Microempresa", "Empresa de Pequeno Porte", "Imune", "Isenta", "Estimativa"]
    
    for row in cursor.fetchall():
        try:
            cod = int(str(row[0]))
            regime = "Outros"
            found = False
            for cell in row:
                s_cell = str(cell)
                for kw in keywords:
                    if kw in s_cell:
                        regime = kw
                        found = True
                        break
                if found: break
            mapping[cod] = regime
        except:
            continue
    return mapping

def get_db_data(cod_list):
    conn = pyodbc.connect(db_conn_str)
    cursor = conn.cursor()
    results = {}
    chunk_size = 500
    for i in range(0, len(cod_list), chunk_size):
        chunk = cod_list[i:i + chunk_size]
        placeholders = ','.join(['?'] * len(chunk))
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
        cursor.execute(q, chunk)
        for row in cursor.fetchall():
            results[row[0]] = (row[1], row[2])
    return results

xls_map = get_xls_map()
db_results = get_db_data(list(xls_map.keys()))

correlacao = {}
for cod, xls_reg in xls_map.items():
    db_vals = db_results.get(cod)
    if db_vals:
        key = (db_vals[0], db_vals[1])
        if key not in correlacao: correlacao[key] = {}
        correlacao[key][xls_reg] = correlacao[key].get(xls_reg, 0) + 1

# Sorting helper for None
def sort_key(item):
    k = item[0]
    return (k[0] if k[0] is not None else -1, k[1] if k[1] is not None else -1)

print(f"{'rfed':<5} | {'sped':<5} | {'Contagem por Regime XLS'}")
print("-" * 80)
for (rfed, sped), counts in sorted(correlacao.items(), key=sort_key):
    counts_str = ", ".join([f"'{k}': {v}" for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)])
    print(f"{str(rfed):<5} | {str(sped):<5} | {counts_str}")
