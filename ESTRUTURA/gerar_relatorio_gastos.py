import pyodbc
import csv
import os

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # 1. Carregar Usuarios
        print("Carregando usuarios...")
        user_dict = {}
        try:
            cursor.execute("SELECT USER_ID_ONVIO, NOME FROM bethadba.usConfUsuario")
            for r in cursor.fetchall():
                if r[0]: 
                    uid = str(r[0]).strip().upper()
                    # normaliza removendo hifens caso a comparacao precise
                    user_dict[uid.replace("-", "")] = r[1]
                    user_dict[uid] = r[1]
        except Exception as e:
            print(f"Aviso users: {e}")

        # 2. Carregar Empresas
        print("Carregando empresas...")
        emp_dict = {}
        try:
            cursor.execute("SELECT GUID_ONVIO, GUID_CONTABIL, nome_emp FROM bethadba.geempre")
            for r in cursor.fetchall():
                nome = r[2]
                g_onvio = str(r[0]).strip().upper() if r[0] else None
                g_contab = str(r[1]).strip().upper() if r[1] else None
                
                if g_onvio:
                    emp_dict[g_onvio.replace("-", "")] = nome
                    emp_dict[g_onvio] = nome
                if g_contab:
                    emp_dict[g_contab.replace("-", "")] = nome
                    emp_dict[g_contab] = nome
        except Exception as e:
            print(f"Aviso emp: {e}")

        # 3. Carregar Atividades Gestta
        print("Carregando Atividades Gestta (Escrita Fiscal 12/2025)...")
        query = """
        SELECT 
            USUARIO,
            EMPRESA,
            ATIVIDADE as Cod_Atividade,
            COMPETENCIA as Competencia,
            MIN(DATAHORACONCLUSAO) as Primeira_Conclusao,
            MAX(DATAHORACONCLUSAO) as Ultima_Conclusao,
            COUNT(CODIGO) as Qtd_Atividades
        FROM bethadba.GEGESTTA_ATIVIDADE
        WHERE COMPETENCIA = '12/2025' AND TIPO_PROCESSAMENTO = 2
        GROUP BY 
            USUARIO,
            EMPRESA,
            ATIVIDADE,
            COMPETENCIA
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        output_file = 'ESTRUTURA/Tempo_Gasto_Escrita_Fiscal_12_2025.csv'
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['Colaborador', 'Cliente', 'Cod_Atividade', 'Competencia', 'Primeira_Conclusao', 'Ultima_Conclusao', 'Qtd_Atividades'])
            
            for row in rows:
                usr_raw = str(row[0]).strip().upper() if row[0] else ''
                emp_raw = str(row[1]).strip().upper() if row[1] else ''
                
                colab = user_dict.get(usr_raw) or user_dict.get(usr_raw.replace("-", "")) or usr_raw
                cliente = emp_dict.get(emp_raw) or emp_dict.get(emp_raw.replace("-", "")) or emp_raw
                
                writer.writerow([
                    colab,
                    cliente,
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6]
                ])
                
        print(f"Relatório gerado com sucesso! Total de linhas: {len(rows)}")
        print(f"Salvo em: {os.path.abspath(output_file)}")
            
    except Exception as e:
        print(f"Erro ao gerar relatorio: {e}")

if __name__ == "__main__":
    main()
