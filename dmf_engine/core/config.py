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
        "db_dsn": "Contabil",
        "db_uid": "EXTERNO",
        "db_timeout": 5,
        "governanca_match_minimo": 2,
        "governanca_bloquear_cnpj_dup": True,
        "governanca_gravar_zero": True,
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
        return cfg

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
