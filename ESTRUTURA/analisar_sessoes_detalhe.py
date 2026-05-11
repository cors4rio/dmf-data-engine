import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Clientes solicitados
        clientes_alvo = [1227, 696]
        
        query = f"""
        SELECT 
            l.usua_log,
            l.codi_emp,
            l.data_log,
            l.tini_log,
            l.tfim_log,
            l.dfim_log,
            DATEDIFF(second, 
                YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tini_log, 
                COALESCE(
                    YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log, 
                    YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log
                )
            ) as segundos
        FROM 
            bethadba.geloguser l
        WHERE 
            l.sist_log = 5
            AND l.tfim_log IS NOT NULL
            AND l.data_log BETWEEN '2026-01-01' AND '2026-01-31'
            AND l.codi_emp IN ({','.join(map(str, clientes_alvo))})
        ORDER BY 
            l.codi_emp, l.data_log, l.tini_log
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        with open(r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\detalhe_sessoes_fiscal.txt', 'w', encoding='utf-8') as f:
            f.write(f"{'EMP':<5} | {'USER':<15} | {'DATA':<10} | {'INICIO':<8} | {'FIM':<8} | {'SEG':<5}\n")
            f.write("-" * 65 + "\n")
            
            totals = {1227: 0, 696: 0}
            for r in rows:
                user, emp, data, tini, tfim, dfim, seg = r
                f.write(f"{emp:<5} | {str(user):<15} | {str(data):<10} | {str(tini):<8} | {str(tfim):<8} | {seg:<5}\n")
                totals[emp] += seg
                
            f.write("\n" + "="*40 + "\n")
            for emp, tot_seg in totals.items():
                h = tot_seg // 3600
                m = (tot_seg % 3600) // 60
                s = tot_seg % 60
                f.write(f"TOTAL EMP {emp}: {h:02d}:{m:02d}:{s:02d} ({tot_seg} seg)\n")

        print("Detalhes salvos em ESTRUTURA/detalhe_sessoes_fiscal.txt")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
