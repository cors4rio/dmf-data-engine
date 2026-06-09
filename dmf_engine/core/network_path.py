r"""
dmf_engine/core/network_path.py
Resolução universal do caminho de rede da plataforma (o antigo "disco Z").

Problema que resolve: a letra mapeada (Z:) é vinculada à sessão/elevação do
Windows — um processo (o exe do app) frequentemente NÃO enxerga o Z: que o
Explorer mostra, especialmente se rodar elevado. Resultado: "Z inacessível"
mesmo com o drive aparecendo no Windows.

Solução: preferir o caminho UNC (\\servidor\share), que é visível a qualquer
processo independente de sessão/letra mapeada. A letra Z: vira só fallback
legado. Exatamente o paralelo da migração do banco para DSN-less.

Uso:
    from dmf_engine.core.network_path import resolver_base, verificar
    base = resolver_base(cfg)          # caminho-raiz acessível (UNC de preferência)
    estado = verificar(cfg)            # {"ok": bool, "base": str, "via": "unc|letra|nenhum"}

Config (chaves universais, no ConfigManager DEFAULTS):
    network_unc    = r"\\srvdmf\CELULAS 2013"     # share de rede (override editável)
    network_subdir = r"#ROTINA AUTOMATICA NF"     # subpasta-base dentro do share
    network_letra  = "Z:"                          # fallback legado
"""
import os
import logging

log = logging.getLogger("NetworkPath")

# Defaults conhecidos da rede DMF (override via config).
UNC_PADRAO    = r"\\srvdmf\CELULAS 2013"
SUBDIR_PADRAO = r"#ROTINA AUTOMATICA NF"
LETRA_PADRAO  = "Z:"


def _cfg(config, chave, default):
    """Lê uma chave do config (dict ou ConfigManager), com default."""
    if config is None:
        return default
    try:
        if hasattr(config, "get"):
            val = config.get(chave, default)
        else:
            val = config.get(chave, default) if isinstance(config, dict) else default
    except Exception:
        val = default
    return val if val else default


def candidatos_base(config=None) -> list:
    """
    Lista de caminhos-raiz candidatos, em ordem de preferência:
      1. UNC + subdir   — universal, visível a qualquer processo
      2. UNC puro       — caso o subdir não exista
      3. Letra + subdir — fallback legado (depende de mapeamento por sessão)
      4. Letra pura
    """
    unc    = _cfg(config, "network_unc",    UNC_PADRAO)
    subdir = _cfg(config, "network_subdir", SUBDIR_PADRAO)
    letra  = _cfg(config, "network_letra",  LETRA_PADRAO)

    cands = []
    if unc:
        cands.append(os.path.join(unc, subdir) if subdir else unc)
        cands.append(unc)
    if letra:
        letra_root = letra if letra.endswith(os.sep) else letra + os.sep
        cands.append(os.path.join(letra_root, subdir) if subdir else letra_root)
        cands.append(letra_root)
    return cands


def resolver_base(config=None) -> str | None:
    """
    Retorna o primeiro caminho-raiz acessível (os.path.isdir confirma), ou None.
    Prefere o UNC — por isso funciona onde a letra Z: mapeada é invisível ao exe.
    """
    for caminho in candidatos_base(config):
        try:
            if os.path.isdir(caminho):
                return caminho
        except Exception:
            continue
    return None


def verificar(config=None) -> dict:
    """
    Estado da disponibilidade do caminho de rede, para a UI.
    Retorna {"ok": bool, "base": str|None, "via": "unc"|"letra"|"nenhum",
             "tentados": [..]}.
    """
    unc    = _cfg(config, "network_unc",   UNC_PADRAO)
    cands  = candidatos_base(config)
    base   = resolver_base(config)
    if base is None:
        return {"ok": False, "base": None, "via": "nenhum", "tentados": cands}
    via = "unc" if base.startswith("\\\\") or (unc and base.startswith(unc)) else "letra"
    return {"ok": True, "base": base, "via": via, "tentados": cands}


def resolver_subpasta(*partes, config=None) -> str | None:
    """
    Resolve um caminho dentro da base de rede (ex: resolver_subpasta('NFe')).
    Retorna o caminho completo se a base for acessível, senão None.
    """
    base = resolver_base(config)
    if base is None:
        return None
    return os.path.join(base, *partes) if partes else base
