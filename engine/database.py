import pyodbc
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DominioDatabase:
    """
    Gerenciador resiliente de conexão ODBC com o banco Domínio (SAP SQL Anywhere 17).
    Isola falhas de conexão para não derrubar o motor principal.

    Conexão DSN-less (preferida): monta a string direto do DRIVER + host/porta/server,
    sem depender do DSN configurado no Windows de cada máquina. Funciona em 32 e 64-bit.
    Fallback DSN (compatibilidade): se nenhum host for informado mas houver um DSN,
    usa `DSN={dsn};...` como antes (modo legado da transição).
    Ver docs/migracao-64bit.md.
    """
    def __init__(self):
        self.dsn      = os.environ.get("DOMINIO_DSN", "Contabil")
        self.uid      = os.environ.get("DOMINIO_UID", "EXTERNO")
        self.pwd      = os.environ.get("DOMINIO_PWD", "")
        self.timeout  = int(os.environ.get("DOMINIO_TIMEOUT", "5"))
        # Parâmetros DSN-less (defaults conhecidos da rede interna)
        self.driver   = os.environ.get("DOMINIO_DRIVER",   "SQL Anywhere 17")
        self.server   = os.environ.get("DOMINIO_SERVER",   "srvlinux")
        self.host     = os.environ.get("DOMINIO_HOST",     "192.168.25.102")
        self.port     = int(os.environ.get("DOMINIO_PORT", "2638"))
        self.database = os.environ.get("DOMINIO_DB",       "contabil")
        self.conn = None
        self.ultimo_erro = None
        self.connection_string = self._montar_connection_string()

    def _montar_connection_string(self) -> str:
        """
        Monta a string de conexão. Prefere DSN-less (host presente); senão DSN legado.
        """
        if self.host:
            return (
                f"DRIVER={self.driver};ENG={self.server};DBN={self.database};"
                f"LINKS=TCPIP{{host={self.host};serverport={self.port}}};"
                f"UID={self.uid};PWD={self.pwd}"
            )
        # Fallback legado — DSN configurado no Windows
        return f"DSN={self.dsn};UID={self.uid};PWD={self.pwd}"

    def configurar(self, dsn=None, uid=None, pwd=None, timeout=None,
                   driver=None, server=None, host=None, port=None, database=None):
        """Atualiza credenciais/parâmetros em runtime (sem reiniciar o app)."""
        if dsn      is not None: self.dsn = dsn
        if uid      is not None: self.uid = uid
        if pwd      is not None: self.pwd = pwd
        if driver   is not None: self.driver = driver
        if server   is not None: self.server = server
        if host     is not None: self.host = host
        if database is not None: self.database = database
        if port is not None:
            try: self.port = int(port)
            except (TypeError, ValueError): pass
        if timeout is not None:
            try: self.timeout = int(timeout)
            except (TypeError, ValueError): pass
        self.connection_string = self._montar_connection_string()
        self.disconnect()

    def configurar_de_cfg(self, cfg: dict):
        """Configura a conexão a partir do dict de config da Central.
        Centraliza o mapeamento config→conexão (DSN-less + fallback DSN)."""
        self.configurar(
            dsn=cfg.get("db_dsn"),
            uid=cfg.get("db_uid"),
            pwd=cfg.get("db_pwd") or self.pwd,
            timeout=cfg.get("db_timeout", 5),
            driver=cfg.get("db_driver"),
            server=cfg.get("db_server"),
            host=cfg.get("db_host"),
            port=cfg.get("db_port"),
            database=cfg.get("db_database"),
        )

    def connect(self):
        """Tenta estabelecer conexao, retorna True se sucesso."""
        try:
            self.conn = pyodbc.connect(self.connection_string, timeout=self.timeout)
            self.ultimo_erro = None
            logging.info("Conexão ODBC com Domínio estabelecida com sucesso.")
            return True
        except Exception as e:
            self.ultimo_erro = str(e)
            alvo = f"{self.host}:{self.port}" if self.host else f"DSN={self.dsn}"
            logging.error(f"Falha ao conectar no banco Domínio ({alvo}): {e}")
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
