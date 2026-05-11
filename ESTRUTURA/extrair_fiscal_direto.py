import pyodbc
from datetime import datetime

def extrair_fiscal_janeiro():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    
    # Lista de logins mapeados dos 24 colaboradores (usua_log na geloguser)
    logins_fiscal = [
        'ALINE.NASCIMENTO', 'ALINE.SANTANA', 'BRENO.MONTEIRO', 'CARINA.RIBEIRO', 
        'CAMILE.GEOVANA', 'CLAUDINEIDE.SILVA', 'ANALISTA.FISCAL2', 'ERON', 'ERVELE.MARQUES', 
        'EZEQUIEL.MELO', 'FERNANDA.RAMOS', 'GEORGE.SANTANA', 'GEOVANA.CRUZ', 
        'ANALISTA.FISCAL3', 'ANALISTA.FISCAL4', 'ANALISTA.FISCAL5', 'ANALISTA.FISCAL6', 'ANALISTA.FISCAL1', 
        'NATALIA.SENA', 'GERENTE.FISCAL', 'COORDENADOR.DP', 'SONILDES.SANDES', 'TAIS.SILVA', 
        'VITOR.HUGO', 'EDUARDO.BONFIM', 'MARIANA.FONSECA'
    ]
    
    # Clientes solicitados
    clientes_alvo = [466, 129]
    
    query = f"""
    SELECT 
        l.usua_log as colaborador,
        l.codi_emp as codigo_cliente,
        e.nome_emp as nome_cliente,
        SUM(DATEDIFF(second, 
            YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tini_log, 
            COALESCE(
				YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log, 
				YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log
			)
        )) as total_segundos
    FROM 
        bethadba.geloguser l
    JOIN 
        bethadba.geempre e ON l.codi_emp = e.codi_emp
    WHERE 
        l.sist_log = 5 -- Módulo Fiscal
        AND l.tfim_log IS NOT NULL -- Sessões finalizadas
        AND l.data_log BETWEEN '2026-01-01' AND '2026-01-31'
        AND l.codi_emp IN ({','.join(map(str, clientes_alvo))})
    GROUP BY 
        l.usua_log, l.codi_emp, e.nome_emp
    ORDER BY 
        l.codi_emp, total_segundos DESC
    """
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print(f"Executando extração para os clientes {clientes_alvo} - Mês 01/2026...")
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("\n" + "="*80)
        print(f"{'CLIENTE':<6} | {'NOME':<40} | {'COLABORADOR':<20} | {'TEMPO'}")
        print("-" * 80)
        
        total_geral_segundos = 0
        for row in results:
            colab, cod, nome, segundos = row
            h = segundos // 3600
            m = (segundos % 3600) // 60
            s = segundos % 60
            tempo_str = f"{h:02d}:{m:02d}:{s:02d}"
            print(f"{cod:<7} | {nome[:40]:<40} | {colab:<20} | {tempo_str}")
            total_geral_segundos += segundos
            
        print("-" * 80)
        h_total = total_geral_segundos // 3600
        m_total = (total_geral_segundos % 3600) // 60
        s_total = total_geral_segundos % 60
        print(f"TOTAL GERAL EXTRAÍDO: {h_total:02d}:{m_total:02d}:{s_total:02d}")
        print("="*80)
        
    except Exception as e:
        print(f"Erro na extração: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    extrair_fiscal_janeiro()
