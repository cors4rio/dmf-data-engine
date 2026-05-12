import sys
import re
from datetime import timedelta
import pyodbc

# Configuraes
FILE_TXT = r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\clientetempogasto022026.txt'
DSN = 'Contabil'
QUERY_FISCAL = """
SELECT 
    e.codi_emp,
    SUM(DATEDIFF(second, 
        YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tini_log,
        COALESCE(
            YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log,
            YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log
        )
    )) as segundos
FROM bethadba.geloguser l
JOIN bethadba.geempre e ON e.codi_emp = l.codi_emp
WHERE l.sist_log = 5
AND l.tfim_log IS NOT NULL
AND l.data_log BETWEEN '2026-02-01' AND '2026-02-28'
GROUP BY e.codi_emp
"""

def parse_txt_time(time_str):
    try:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return 0
    except:
        return 0

def hms(seconds):
    if seconds is None: return "00:00:00"
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def main():
    print("--- COMPARATIVO FISCAL (TXT vs BANCO) ---")
    
    # 1. Carregar TXT
    dict_txt = {}
    try:
        with open(FILE_TXT, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        return

    for line in content.splitlines():
        match = re.search(r'^\s*(\d+)\s+.*?\s+(\d+:\d{2}:\d{2})\s*$', line.strip())
        if match:
            cod = int(match.group(1))
            tempo_str = match.group(2)
            dict_txt[cod] = parse_txt_time(tempo_str)

    print(f"Empresas no TXT: {len(dict_txt)}")

    # 2. Carregar Banco
    dict_db = {}
    try:
        conn = pyodbc.connect(f'DSN={DSN};UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
        cursor = conn.cursor()
        print("Buscando dados no DB...")
        cursor.execute(QUERY_FISCAL)
        for row in cursor.fetchall():
            dict_db[row.codi_emp] = int(row.segundos)
        conn.close()
    except Exception as e:
        print(f"Erro ODBC: {e}")
        return

    print(f"Empresas no Banco: {len(dict_db)}")

    # 3. Comparar
    all_codes = sorted(set(dict_txt.keys()) | set(dict_db.keys()))
    
    report = ["| Codigo | Tempo TXT | Tempo Banco | Diferenca | Status |", "|---|---|---|---|---|"]
    matches = 0
    diffs = 0
    only_txt = 0
    only_db = 0

    for cod in all_codes:
        t_txt = dict_txt.get(cod)
        t_db = dict_db.get(cod)
        
        if t_txt is None:
            if t_db > 0:
                report.append(f"| {cod} | - | {hms(t_db)} | - | S Banco |")
                only_db += 1
        elif t_db is None:
            if t_txt > 0:
                report.append(f"| {cod} | {hms(t_txt)} | - | - | S TXT |")
                only_txt += 1
        else:
            diff = abs(t_txt - t_db)
            if diff <= 2:
                matches += 1
            else:
                report.append(f"| {cod} | {hms(t_txt)} | {hms(t_db)} | {diff}s | DIVERGENTE |")
                diffs += 1

    print(f"Matches: {matches}")
    print(f"Divergencias: {diffs}")
    print(f"So no TXT: {only_txt}")
    print(f"So no Banco: {only_db}")

    with open('relatorio_comparativo_fiscal.md', 'w', encoding='utf-8') as f:
        f.write("# Relatorio de Comparacao Fiscal (Fev/2026)\n\n")
        f.write(f"- Arquivo: `clientetempogasto022026.txt` vs Banco Domínio\n")
        f.write(f"- Matches: {matches}\n")
        f.write(f"- Divergencias: {diffs}\n")
        f.write(f"- So no TXT: {only_txt}\n")
        f.write(f"- So no Banco: {only_db}\n\n")
        f.write("\n".join(report))
    
    print("Relatorio salvo com sucesso.")

if __name__ == "__main__":
    main()
