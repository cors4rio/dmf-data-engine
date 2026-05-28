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
        self.pwd = os.environ.get("DOMINIO_PWD", "")
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
        Executa a query e retorna lista de dicionários, com reconexão transparente.

        Resiliência:
          - B04: se a conexão estiver morta (Sybase fechou por inatividade, rede caiu),
            detecta via pyodbc.Error e reconecta UMA vez antes de desistir.
          - B05: cursor.description é None em queries sem result set (UPDATE/DELETE).
            Detecta e retorna [] com log explícito em vez de TypeError silencioso.

        Sempre retorna lista (vazia em caso de falha) para não derrubar os módulos.
        """
        max_tentativas = 2
        for tentativa in range(max_tentativas):
            if not self.conn:
                if not self.connect():
                    return []

            cursor = None
            try:
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # B05: queries DML (UPDATE/DELETE/SET) não retornam description
                if cursor.description is None:
                    logging.warning(f"[DB] Query sem result set (DML?): {query[:80]}...")
                    return []

                columns = [column[0] for column in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results

            except pyodbc.Error as e:
                # Conexão pode ter sido derrubada — tenta reconectar UMA vez
                logging.warning(f"[DB] pyodbc.Error (tentativa {tentativa+1}/{max_tentativas}): {e}")
                self.disconnect()
                if tentativa == max_tentativas - 1:
                    self.ultimo_erro = str(e)
                    logging.error(f"[DB] Query falhou após reconexão: {e}")
                    return []
                continue  # próxima iteração reconecta
            except Exception as e:
                logging.error(f"[DB] Erro inesperado ao executar query: {e}")
                self.ultimo_erro = str(e)
                return []
            finally:
                if cursor is not None:
                    try:
                        cursor.close()
                    except Exception:
                        pass
        return []

# Instância global para uso nos módulos
db = DominioDatabase()
