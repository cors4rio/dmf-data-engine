import pyodbc

conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()

# Ver detalhes dos contribuintes da 614
print('=== CONTRIBUINTES (vinculo=11) DA EMPRESA 614 ===')
cursor.execute("""
    SELECT e.i_empregados, e.nome, e.admissao
    FROM bethadba.foempregados e
    WHERE e.codi_emp = 614
      AND e.vinculo = 11
    ORDER BY e.admissao DESC
""")
rows = cursor.fetchall()
print(f'Total contribuintes: {len(rows)}')
print()
for r in rows:
    print(f'  i_emp={r[0]:5d} nome={str(r[1])[:40]:40s} admissao={r[2]}')

# Agora verificar: a planilha da Carol tinha quantos para essa empresa?
# Verificar se contribuintes TEM rescisao em OUTRA tabela
print()
print('=== VERIFICAR se ha tabela de encerramento de contribuinte ===')

# Talvez para contribuintes, o correto é verificar foparmto ou outra tabela
# Vamos verificar se existe pagamento recente (competencia 04/2026) para esses contribuintes
print()
print('=== VERIFICAR FOLHA CALCULADA (focalculo) PARA EMPRESA 614 ===')
try:
    cursor.execute("""
        SELECT COUNT(*) as total, MAX(competencia) as ult_comp
        FROM bethadba.focalculo
        WHERE codi_emp = 614
    """)
    r = cursor.fetchone()
    print(f'  Total registros focalculo: {r[0]}, Ultima competencia: {r[1]}')
except Exception as e:
    print(f'  focalculo nao encontrada: {e}')

# Tentar fomovimento
print()
print('=== VERIFICAR MOVIMENTOS RECENTES EMPRESA 614 ===')
try:
    cursor.execute("""
        SELECT competencia, COUNT(*) as qtd
        FROM bethadba.fomovimento
        WHERE codi_emp = 614
          AND competencia >= '2026-01-01'
        GROUP BY competencia
        ORDER BY competencia DESC
    """)
    for r in cursor.fetchall():
        print(f'  competencia={r[0]} qtd_movimentos={r[1]}')
except Exception as e:
    print(f'  fomovimento: {e}')

# Verificar fofolhapagto
print()
print('=== VERIFICAR FOLHA PAGAMENTO EMPRESA 614 (2026) ===')
try:
    cursor.execute("""
        SELECT e.i_empregados, e.vinculo, f.competencia
        FROM bethadba.fofolhapagto f
        JOIN bethadba.foempregados e 
            ON e.codi_emp = f.codi_emp AND e.i_empregados = f.i_empregados
        WHERE f.codi_emp = 614
          AND f.competencia >= '2026-04-01'
          AND e.vinculo = 11
    """)
    rows = cursor.fetchall()
    print(f'  Contribuintes com folha em 04/2026+: {len(rows)}')
    for r in rows:
        print(f'    emp={r[0]} vinculo={r[1]} competencia={r[2]}')
except Exception as e:
    print(f'  fofolhapagto: {e}')

conn.close()
