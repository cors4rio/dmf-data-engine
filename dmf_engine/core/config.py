"""
dmf_engine/core/config.py
ConfigManager — única fonte de verdade para config.json.
Extraído de Api._ler_config() e Api.salvar_parametros() de main.py.
"""
import os
import json
import logging

log = logging.getLogger("ConfigManager")


class ConfigManager:
    """
    Gerencia config.json com defaults declarados e merge transparente.

    Substitui _ler_config() e salvar_parametros() que existiam inline na Api.
    Todos os módulos acessam configurações via self._config.get(key) ou self._config.load().
    """

    DEFAULTS = {
        "fiscal_adicional_pct": 80,
        "dp_fator_carga": 0.33,
        "dp_overhead_fixo": 1.5,
        "dp_apenas_socios": 1.0,
        "dp_tempo_minimo": 5.0,
        "dp_consultoria_horas": 1.5,
        "contabil_origem_path": r"C:\Users\DMF-AUTOMACAO\OneDrive - DMF\DMF - Documentos\Administrativo\HORAS CONTABEIS.xlsx",
        "contabil_aplicar_excecoes": True,
        # Conexão com o banco Domínio (SAP SQL Anywhere 17).
        # DSN-less (preferido): host/porta/server/driver montam a string direto,
        # sem depender do DSN do Windows. db_dsn fica só como fallback legado.
        # Ver docs/migracao-64bit.md.
        "db_dsn":      "Contabil",       # fallback legado (modo DSN)
        "db_uid":      "EXTERNO",
        "db_pwd":      "",
        "db_timeout":  5,
        "db_driver":   "SQL Anywhere 17",
        "db_server":   "srvlinux",
        "db_host":     "192.168.25.102",
        "db_port":     2638,
        "db_database": "contabil",
        "governanca_match_minimo": 2,
        "governanca_bloquear_cnpj_dup": True,
        "governanca_gravar_zero": True,
        # Override OPCIONAL do Python 32-bit que lança o automacao_horas.
        # Vazio = o launcher descobre automaticamente via `py -3-32` (ver
        # _resolver_python_32 em m_automacao_horas.py). Só preencha para forçar
        # um interpretador específico.
        "automacao_horas_python": "",
        # Sem Movimento NFS-e Salvador
        "sm_anticaptcha_api_key":     "",
        "sm_headless":               True,
        "sm_captcha_timeout_s":      60,
        "sm_pausa_entre_empresas_s": 2,
        # TFF Salvador
        "tf_anticaptcha_api_key":     "",
        "tf_headless":               True,
        "tf_captcha_timeout_s":      60,
        "tf_pausa_entre_clientes_s": 3,
    }

    def __init__(self, config_path: str):
        self._path = config_path

    def load(self) -> dict:
        cfg = dict(self.DEFAULTS)
        if os.path.exists(self._path):
            try:
                with open(self._path, encoding="utf-8") as f:
                    saved = json.load(f)
                cfg.update(saved)
            except Exception as e:
                log.warning(f"Falha ao ler config.json: {e}")
        self._migrar(cfg)
        return cfg

    @staticmethod
    def _migrar(cfg: dict) -> None:
        """Auto-correções de configs legadas, aplicadas a cada load.
        Configs de produção têm valores antigos gravados que quebram a conexão;
        corrigir aqui é self-healing em toda máquina (ver docs/migracao-64bit.md)."""
        # db_uid="dba" nunca autentica no banco Domínio — o usuário real é EXTERNO.
        if str(cfg.get("db_uid", "")).strip().lower() == "dba":
            cfg["db_uid"] = "EXTERNO"

    def save(self, updates: dict) -> bool:
        cfg = self.load()
        cfg.update(updates)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            log.info(f"[CONFIG] Salvo: {list(updates.keys())}")
            return True
        except Exception as e:
            log.error(f"[CONFIG] Falha ao salvar: {e}")
            return False

    def get(self, key: str, default=None):
        return self.load().get(key, default)
