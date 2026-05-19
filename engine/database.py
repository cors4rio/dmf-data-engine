import pyodbc
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DominioDatabase:
    """
    Gerenciador resiliente de conexão ODBC com o banco Domínio (Sybase).
    Isola falhas de conexão para não derrubar o motor principal.
    """
    def __init__(self):
        self.dsn = os.environ.get("DOMINIO_DSN", "Contabil")
        self.uid = os.environ.get("DOMINIO_UID", "EXTERNO")
        self.pwd = os.environ.get("DOMINIO_PWD", "***REDACTED***")
        self.timeout = int(os.environ.get("DOMINIO_TIMEOUT", "5"))
        self.connection_string = f"DSN={self.dsn};UID={self.uid};PWD={self.pwd}"
        self.conn = None
        self.ultimo_erro = None

    def configurar(self, dsn=None, uid=None, pwd=None, timeout=None):
        """Atualiza credenciais em runtime (sem reiniciar o app)."""
        if dsn is not None: self.dsn = dsn
        if uid is not None: self.uid = uid
        if pwd is not None: self.pwd = pwd
        if timeout is not None:
            try: self.timeout = int(timeout)
            except (TypeError, ValueError): pass
        self.connection_string = f"DSN={self.dsn};UID={self.uid};PWD={self.pwd}"
        self.disconnect()

    def connect(self):
        """Tenta estabelecer conexao, retorna True se sucesso."""
        try:
            self.conn = pyodbc.connect(self.connection_string, timeout=self.timeout)
            self.ultimo_erro = None
            logging.info("Conexão ODBC com Domínio estabelecida com sucesso.")
            return True
        except Exception as e:
            self.ultimo_erro = str(e)
            logging.error(f"Falha ao conectar no banco Domínio (DSN={self.dsn}): {e}")
            return False

    def disconnect(self):
        """Fecha a conexão."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logging.info("Conexão ODBC fechada.")

    def fetch_all(self, query, params=None):
        """
        Executa a query e retorna uma lista de dicionários.
        Se falhar, retorna lista vazia e não trava o script.
        """
        if not self.conn:
            if not self.connect():
                return []
        
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                # Converter None do Sybase para valores utilizáveis se necessário,
                # ou manter None e tratar nos módulos.
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            logging.error(f"Erro ao executar query: {e}")
            return []
        finally:
            cursor.close()

# Instância global para uso nos módulos
db = DominioDatabase()
