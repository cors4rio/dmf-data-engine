import re
import os

def time_to_str(decimal_hours):
    if isinstance(decimal_hours, str): return decimal_hours
    total_seconds = int(decimal_hours * 3600)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    return f"{h:02d}:{m:02d}"

def clean_name(name):
    return re.sub(r"\s+", " ", name).strip().upper()

exceptions = {}
consultoria = {}

path_exc = r"C:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\nao_faz_setor\DP NAO.txt"
if os.path.exists(path_exc):
    with open(path_exc, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "EMPRESAS QUE" in line: continue
            is_consult = "CONSULTORIA" in line.upper()
            match = re.match(r"^(\d+)[ \t;]", line)
            if match:
                code = match.group(1)
                raw_name = line[len(code):].strip().split("(")[0].strip(" \t;")
                name = clean_name(raw_name)
                if is_consult: consultoria[code] = name
                else: exceptions[code] = name
            else:
                name = clean_name(line.split("(")[0].strip())
                if is_consult: consultoria[name] = True
                else: exceptions[name] = True

path_folha = r"C:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\FOLHA032026.txt"
with open(path_folha, "r", encoding="utf-8") as f:
    lines = f.readlines()

output = []
output.append("# Relatório de Cálculo: Folha de Pagamento - Competência 03/2026\n")
output.append("> **Fonte:** `FOLHA032026.txt` | **Regras:** `Spec_Folha_Pagamento.md` | **Exceções:** `DP NAO.txt` \n")
output.append("| Código | Empresa | Ativos (F+E+C) | Tipo/Cálculo | Tempo Gasto (DP) |")
output.append("|---|---|---|---|---|")

for line in lines:
    line = line.strip()
    if not line: continue
    parts = line.split("\t")
    if len(parts) < 6: continue
    
    cod = parts[0].strip()
    if not cod.isdigit() or cod == "Código": continue
    
    nome_raw = parts[1].strip()
    nome = clean_name(nome_raw)
    
    try:
        f_str = parts[3].strip()
        e_str = parts[4].strip()
        c_str = parts[5].strip()
        func = int(f_str) if f_str.isdigit() else 0
        estag = int(e_str) if e_str.isdigit() else 0
        contrib = int(c_str) if c_str.isdigit() else 0
    except:
        func, estag, contrib = 0, 0, 0
    
    total = func + estag + contrib
    
    if cod in consultoria or nome in consultoria:
        calc_str = "Flag: Consultoria"
        final_val = "01:30"
    elif cod in exceptions or nome in exceptions:
        calc_str = "Flag: DP NÃO"
        final_val = "DP NÃO"
    else:
        if total > 0:
            decimal = (total * 0.33) + 1.5
            calc_str = f"({total} * 0.33) + 1.5"
            final_val = time_to_str(decimal)
        else:
            calc_str = "Mínimo (0:05)"
            final_val = "00:05"
    
    output.append(f"| {cod} | {nome_raw} | {total} | {calc_str} | **{final_val}** |")

with open("calculo_folha_report_utf8.md", "w", encoding="utf-8") as f:
    f.write("\n".join(output))
