import pyodbc
conn = pyodbc.connect('DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>')
cursor = conn.cursor()
for row in cursor.tables(tableType='TABLE'):
    if row.table_name.startswith('ef'):
        print(row.table_name)
