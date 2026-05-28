"""Autenticação local com lista de supervisores e amarração de máquina.

Lista de usuários autorizados carregada de `usuarios.json` (não rastreado).
Copie `usuarios_template.json` → `usuarios.json` e preencha com os dados reais.
O arquivo `supervisores.json` guarda apenas estado de runtime
(hash, salt, máquina amarrada, flag de primeira senha).

Identificação de máquina = `hostname\\username`. Não é à prova de adversário
sofisticado, mas impede que uma pessoa entre na conta da outra mesmo tendo a senha.
"""

import os
import json
import hashlib
import hmac
import secrets
import socket
import logging
from datetime import datetime


# ── Usuários autorizados (carregados de arquivo externo) ──────────────────
_AUTH_DIR = os.path.dirname(os.path.abspath(__file__))
_USUARIOS_FILE = os.path.join(_AUTH_DIR, "usuarios.json")

USUARIOS_AUTORIZADOS = []
if os.path.exists(_USUARIOS_FILE):
    try:
        with open(_USUARIOS_FILE, "r", encoding="utf-8") as _f:
            USUARIOS_AUTORIZADOS = json.load(_f)
    except Exception as _e:
        logging.warning(f"[AUTH] Não foi possível ler usuarios.json: {_e}")
else:
    logging.warning("[AUTH] usuarios.json não encontrado. Copie usuarios_template.json → usuarios.json")

# Quais módulos cada papel pode executar (escrita)
PERMISSOES_EXECUCAO = {
    "admin":       {"fiscal", "contabil", "dp"},
    "contabil":    {"contabil"},
    "fiscal":      {"fiscal"},
    "dp":          {"dp"},
    "legalizacao": set(),
}

ITERACOES = 120_000
SALT_BYTES = 16


# ── Helpers ────────────────────────────────────────────────

def _arquivo(base_dir):
    return os.path.join(base_dir, "supervisores.json")


def _hash_senha(senha, salt_hex):
    salt = bytes.fromhex(salt_hex)
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, ITERACOES).hex()


def _carregar(base_dir):
    caminho = _arquivo(base_dir)
    if not os.path.exists(caminho):
        return {"supervisores": []}
    try:
        with open(caminho, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("supervisores", [])
        return data
    except Exception as e:
        logging.error(f"[AUTH] Falha ao ler {caminho}: {e}")
        return {"supervisores": []}


def _gravar(base_dir, data):
    try:
        with open(_arquivo(base_dir), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"[AUTH] Falha ao gravar: {e}")
        return False


def _buscar(data, nome):
    n = (nome or "").lower()
    for s in data["supervisores"]:
        if s["nome"].lower() == n:
            return s
    return None


def identificar_maquina():
    """Fingerprint local da máquina: hostname + usuário Windows."""
    host = socket.gethostname() or "unknown_host"
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown_user"
    return f"{host}\\{user}"


def _config_usuario(nome):
    """Retorna a entrada de USUARIOS_AUTORIZADOS para o nome ou None."""
    n = (nome or "").lower()
    for u in USUARIOS_AUTORIZADOS:
        if u["nome"] == n:
            return u
    return None


# ── Inicialização (chamada no boot) ───────────────────────

def inicializar_supervisores_padrao(base_dir):
    """Sincroniza supervisores.json com USUARIOS_AUTORIZADOS.

    - Cria entradas faltantes com senha padrão = nome em minúsculas, primeira_senha=True.
    - Remove entradas que não estão mais autorizadas.
    - Atualiza papéis (caso tenhamos mudado a tabela em código).
    - Preserva hash/salt/máquina dos usuários existentes.
    """
    data = _carregar(base_dir)
    autorizados_nomes = {u["nome"] for u in USUARIOS_AUTORIZADOS}

    # Remove não-autorizados
    data["supervisores"] = [
        s for s in data["supervisores"] if s["nome"].lower() in autorizados_nomes
    ]

    nomes_existentes = {s["nome"].lower() for s in data["supervisores"]}
    for u in USUARIOS_AUTORIZADOS:
        existente = _buscar(data, u["nome"])
        if existente is None:
            # Cria com senha padrão = nome em minúsculas, primeira_senha=True
            salt_hex = secrets.token_hex(SALT_BYTES)
            data["supervisores"].append({
                "nome": u["nome"],
                "label": u["label"],
                "papel": u["papel"],
                "salt": salt_hex,
                "hash": _hash_senha(u["nome"], salt_hex),
                "maquina": None,
                "primeira_senha": True,
                "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "ultimo_login": None,
            })
            logging.info(f"[AUTH] Criado supervisor padrão: {u['label']} ({u['papel']})")
        else:
            # Atualiza papel/label se mudou em código
            existente["papel"] = u["papel"]
            existente["label"] = u["label"]
            existente.setdefault("primeira_senha", False)
            existente.setdefault("maquina", None)
            existente.setdefault("ultimo_login", None)

    _gravar(base_dir, data)


# ── API pública ────────────────────────────────────────────

def listar_supervisores(base_dir):
    data = _carregar(base_dir)
    return [
        {
            "nome": s["nome"],
            "label": s.get("label", s["nome"].title()),
            "papel": s.get("papel"),
            "maquina": s.get("maquina"),
            "primeira_senha": bool(s.get("primeira_senha")),
            "ultimo_login": s.get("ultimo_login"),
        }
        for s in data["supervisores"]
    ]


def autenticar(base_dir, nome, senha):
    """Verifica nome+senha+máquina. Retorna dict com sinalizadores:
      - ok=True: autenticado, OK pra entrar
      - precisa_trocar_senha=True: ok mas precisa trocar antes de continuar
      - maquina_bloqueada=True: senha bate mas a máquina não é a amarrada
      - ok=False, erro='...': falha de credencial
    """
    if not nome or not senha:
        return {"ok": False, "erro": "Informe usuário e senha."}
    data = _carregar(base_dir)
    s = _buscar(data, nome)
    if not s:
        return {"ok": False, "erro": "Usuário ou senha incorretos."}

    h = _hash_senha(senha, s["salt"])
    if not hmac.compare_digest(s["hash"], h):
        return {"ok": False, "erro": "Usuário ou senha incorretos."}

    if s.get("primeira_senha"):
        return {
            "ok": True,
            "precisa_trocar_senha": True,
            "nome": s["nome"], "label": s.get("label"), "papel": s.get("papel"),
        }

    maquina_atual = identificar_maquina()
    maquina_amarrada = s.get("maquina")
    if maquina_amarrada and maquina_amarrada != maquina_atual:
        return {
            "ok": False, "maquina_bloqueada": True,
            "erro": (f"Esta conta está vinculada a outra máquina "
                     f"({maquina_amarrada}). Peça ao admin para liberar."),
        }

    s["ultimo_login"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    if not maquina_amarrada:
        s["maquina"] = maquina_atual
    _gravar(base_dir, data)

    return {
        "ok": True,
        "nome": s["nome"], "label": s.get("label"), "papel": s.get("papel"),
        "maquina": s.get("maquina"),
    }


def trocar_senha_primeiro_acesso(base_dir, nome, senha_atual, senha_nova):
    """Usado quando precisa_trocar_senha=True. Amarra a máquina simultaneamente."""
    if not senha_nova or len(senha_nova) < 4:
        return {"ok": False, "erro": "Nova senha precisa ter pelo menos 4 caracteres."}
    if senha_nova.lower() == (nome or "").lower():
        return {"ok": False, "erro": "Escolha uma senha diferente do seu usuário."}
    data = _carregar(base_dir)
    s = _buscar(data, nome)
    if not s:
        return {"ok": False, "erro": "Usuário não encontrado."}
    if not hmac.compare_digest(s["hash"], _hash_senha(senha_atual, s["salt"])):
        return {"ok": False, "erro": "Senha atual incorreta."}
    s["salt"] = secrets.token_hex(SALT_BYTES)
    s["hash"] = _hash_senha(senha_nova, s["salt"])
    s["primeira_senha"] = False
    s["maquina"] = identificar_maquina()
    s["ultimo_login"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    _gravar(base_dir, data)
    logging.info(f"[AUTH] {nome} trocou senha e foi amarrado a {s['maquina']}.")
    return {
        "ok": True,
        "nome": s["nome"], "label": s.get("label"), "papel": s.get("papel"),
        "maquina": s.get("maquina"),
    }


def trocar_senha(base_dir, nome, senha_atual, senha_nova):
    """Troca de senha voluntária (após já estar autenticado)."""
    if not senha_nova or len(senha_nova) < 4:
        return {"ok": False, "erro": "Nova senha precisa ter pelo menos 4 caracteres."}
    data = _carregar(base_dir)
    s = _buscar(data, nome)
    if not s:
        return {"ok": False, "erro": "Usuário não encontrado."}
    if not hmac.compare_digest(s["hash"], _hash_senha(senha_atual, s["salt"])):
        return {"ok": False, "erro": "Senha atual incorreta."}
    s["salt"] = secrets.token_hex(SALT_BYTES)
    s["hash"] = _hash_senha(senha_nova, s["salt"])
    _gravar(base_dir, data)
    return {"ok": True}


# ── Operações de admin ────────────────────────────────────

def liberar_maquina(base_dir, nome):
    data = _carregar(base_dir)
    s = _buscar(data, nome)
    if not s:
        return {"ok": False, "erro": "Usuário não encontrado."}
    s["maquina"] = None
    _gravar(base_dir, data)
    logging.info(f"[AUTH] Máquina liberada para {nome}.")
    return {"ok": True}


def resetar_senha(base_dir, nome):
    """Volta o usuário para a senha padrão e força troca no próximo login."""
    data = _carregar(base_dir)
    s = _buscar(data, nome)
    if not s:
        return {"ok": False, "erro": "Usuário não encontrado."}
    s["salt"] = secrets.token_hex(SALT_BYTES)
    s["hash"] = _hash_senha(s["nome"], s["salt"])
    s["primeira_senha"] = True
    _gravar(base_dir, data)
    logging.info(f"[AUTH] Senha resetada para {nome}.")
    return {"ok": True}


# ── Autorização ────────────────────────────────────────────

def pode_executar(papel, modulo):
    """`modulo` ∈ {'fiscal', 'contabil', 'dp'}. `papel` é a string da entrada."""
    if not papel:
        return False
    return modulo in PERMISSOES_EXECUCAO.get(papel, set())
