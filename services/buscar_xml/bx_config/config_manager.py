"""
config_manager.py — Leitura e escrita do config.json.
Substitui as variáveis de ambiente do .env antigo.
"""

import os
import json

DEFAULT_CONFIG = {
    "erp": {
        "usuario":       "icaro.dmf",
        "senha":         "",
        "url_base":      "https://erp.bluesoft.com.br/agromixatalaia",
        "email_destino": "dmfautomacoes@gmail.com",
    },
    "nfce": {
        "url_base": "http://10.111.246.241:9091/nfx/",
        "usuario":  "198",
        "senha":    "123456",
    },
    "nfe": {
        "timeout_aguardo_min":   30,   # tempo máx. para os ZIPs chegarem na rede após disparo
        "intervalo_check_s":     10,   # checagem da pasta de rede durante o aguardo
    },
    "imap": {
        "servidor":        "imap.gmail.com",
        "porta":           993,
        "usuario":         "",
        "senha":           "",
        "idle_max_ciclos": 5,  # ciclos sem e-mail → encerra daemon da sessão
    },
    "paths": {
        "base_z": r"Z:\#ROTINA AUTOMATICA NF",
        "nfe":    r"Z:\#ROTINA AUTOMATICA NF\NFe",
        "nfce":   r"Z:\#ROTINA AUTOMATICA NF\NFCe",
        "sped":   r"Z:\#ROTINA AUTOMATICA NF\SPED",
    },
    "telegram": {
        "bot_token": "",
        "chat_id":   "",
    },
    "sped": {
        "timeout_drive_tentativas": 30,
        "timeout_drive_segundos":   20,
    },
    "admin": {
        "senha_hash": "",  # SHA-256 hex; vazio = sem senha (primeiro uso)
    },
    "tokai": {
        "sharepoint_url":     "",
        "email_user":         "",
        "gmail_label":        "TOKAI - XML",
        "storage_state_path": "",
        "motor_path":         r"C:\Users\DMF-AUTOMACAO\Documents\PROJETOS\buscador_xml\auto_tokai",
        "network_path":       r"Z:\#ROTINA AUTOMATICA NF",
        "max_email_age_days": 35,
        "headless_mode":      False,
    },
}


class ConfigManager:
    def __init__(self, base_dir: str):
        # Dados de runtime ficam em bx_data/ (não em "config", que se confundia
        # com o pacote de código bx_config/). Migra automaticamente de config/
        # legado, se existir, para não perder o config.json do usuário.
        self._path = os.path.join(base_dir, "bx_data", "config.json")
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        _legado = os.path.join(base_dir, "config", "config.json")
        if os.path.exists(_legado) and not os.path.exists(self._path):
            try:
                import shutil
                shutil.move(_legado, self._path)
            except Exception:
                pass

    def load(self) -> dict:
        if not os.path.exists(self._path):
            self.save(DEFAULT_CONFIG)
            return _deep_copy(DEFAULT_CONFIG)
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                dados = json.load(f)
            return _merge(DEFAULT_CONFIG, dados)
        except Exception:
            return _deep_copy(DEFAULT_CONFIG)

    def save(self, dados: dict) -> dict:
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            if os.path.exists(self._path):
                os.remove(self._path)
            os.rename(tmp, self._path)
            return {"ok": True}
        except Exception as e:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
            return {"ok": False, "msg": str(e)}


def _merge(default: dict, override: dict) -> dict:
    result = _deep_copy(default)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _merge(result[k], v)
        else:
            result[k] = v
    return result


def _deep_copy(d):
    return json.loads(json.dumps(d))
