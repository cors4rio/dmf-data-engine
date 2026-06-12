"""
engine/tokai_adapter.py
Adapter do motor AUTO_TOKAI para o AGROMIX_UI.
Remove: schedule, loguru, dotenv.
Adiciona: stop_flag, progress_cb, config dict.
"""

import os
import sys
import logging
import threading
import zipfile
import subprocess
import shutil

from .bx_playwright_compat import (
    configurar_browsers_path, policy_proactor, suprimir_janelas_subprocess,
)

log = logging.getLogger("TOKAI")

# Caminho do motor TOKAI. Agora o motor vive DENTRO do projeto (unificado), em
# services/buscar_xml/tokai_motor/ — irmão de bx_engine/. Resolve em dev e no exe.
# Ainda pode ser sobrescrito por config["tokai"]["motor_path"] (compat. legado).
def _resolver_motor_dir() -> str:
    """Resolve o motor_path. PREGUIÇOSO: a sincronização no exe (cópia para pasta
    gravável) só acontece quando chamado — não no import do módulo, p/ não pesar o boot."""
    # Dev: tokai_motor é irmão de bx_engine/ (services/buscar_xml/tokai_motor),
    # gravável no próprio repo.
    if not getattr(sys, "frozen", False):
        aqui = os.path.dirname(os.path.abspath(__file__))       # .../bx_engine
        cand = os.path.normpath(os.path.join(aqui, "..", "tokai_motor"))
        if os.path.isdir(cand):
            return cand
        # Fallback legado: caminho externo antigo.
        return r"C:\Users\DMF-AUTOMACAO\Documents\PROJETOS\buscador_xml\auto_tokai"

    # No exe (frozen): o motor é empacotado read-only no _MEIPASS, mas o motor
    # ESCREVE (token.json, playwright_storage.json, logs). Então sincronizamos o
    # CÓDIGO para uma pasta gravável ao lado do exe e usamos ela como motor_path.
    # Arquivos sensíveis/sessão (credenciais, token, storage) que o usuário já
    # tenha lá são PRESERVADOS (nunca sobrescritos pelo bundle).
    # Apenas o caminho-alvo (gravável). A cópia real é feita por _preparar_motor()
    # quando o TOKAI é executado, não aqui (mantém o boot leve).
    return os.path.join(os.path.dirname(sys.executable), "tokai_motor")


def _motor_path_efetivo(config: dict) -> str:
    """Resolve o motor_path a usar, com migração do caminho legado.

    - motor_path vazio no config → usa o motor unificado (TOKAI_DIR = tokai_motor).
    - motor_path = caminho externo legado (buscador_xml/auto_tokai) → IGNORA e usa o
      unificado se este existir. Evita que máquinas com config antigo fiquem presas
      no motor externo após a unificação.
    - motor_path customizado (outro caminho) → respeita (compatibilidade).
    """
    mp = (config.get("tokai", {}).get("motor_path", "") or "").strip()
    if not mp:
        return TOKAI_DIR
    # Caminho legado conhecido → migra para o unificado.
    if "buscador_xml" in mp.replace("/", "\\").lower() and os.path.isdir(TOKAI_DIR):
        log.info(f"motor_path legado ('{mp}') ignorado — usando motor unificado: {TOKAI_DIR}")
        return TOKAI_DIR
    return mp


def _preparar_motor(tokai_dir: str):
    """No exe, garante que o código do motor está na pasta gravável `tokai_dir`
    (sincronizado do bundle _MEIPASS, preservando credenciais). No-op em dev."""
    if not getattr(sys, "frozen", False):
        return
    bundle = os.path.join(sys._MEIPASS, "tokai_motor")
    _sincronizar_motor(bundle, tokai_dir)


# Arquivos que o usuário cria/edita por máquina — NUNCA sobrescrever no update.
_MOTOR_PRESERVAR = {
    ".env", "credentials.json", "token.json",
    "playwright_storage.json", "playwright_storage.json.bak",
    "config_clientes.json",
}


def _sincronizar_motor(bundle: str, destino: str):
    """Copia o código do motor (bundle read-only) para a pasta gravável, sem
    tocar nos arquivos sensíveis/de sessão que o usuário já tenha no destino."""
    import shutil
    if not os.path.isdir(bundle):
        raise RuntimeError(f"Motor empacotado ausente em {bundle}")
    os.makedirs(destino, exist_ok=True)
    for raiz, _dirs, arquivos in os.walk(bundle):
        rel = os.path.relpath(raiz, bundle)
        dst_dir = destino if rel == "." else os.path.join(destino, rel)
        os.makedirs(dst_dir, exist_ok=True)
        for nome in arquivos:
            dst = os.path.join(dst_dir, nome)
            # Preserva credenciais/sessão já existentes na máquina.
            if nome in _MOTOR_PRESERVAR and os.path.exists(dst):
                continue
            try:
                shutil.copy2(os.path.join(raiz, nome), dst)
            except Exception:
                pass

_DEFAULT_TOKAI_DIR = _resolver_motor_dir()
TOKAI_DIR = _DEFAULT_TOKAI_DIR

# (sp_name, codigo_dominio, nome_dominio, regiao)
# sp_name deve corresponder exatamente a uma chave em AUTO_TOKAI/src/domain/config.CLIENT_MAPPING
TOKAI_CLIENTS_DISPLAY = [
    # BH
    ("FMM",             "558",  "FMM_10642",           "BH"),
    ("GAD",             "560",  "GAD_COMERCIO 10649",  "BH"),
    ("MAD",             "559",  "MAD_10644",            "BH"),
    # BL
    ("EAC",             "564",  "EAC_10636",            "BL"),
    ("GFD",             "575",  "GFD REST_10633",       "BL"),
    ("RSC",             "566",  "RSC_10641",            "BL"),
    # MN
    ("LSM",             "553",  "LSM_10639",            "MN"),
    # REC
    ("LMS",             "569",  "LMS RECIFE_10646",     "REC"),
    ("LOTTI RIO MAR",   "574",  "LOTTI RIO MAR",        "REC"),
    ("MISSKOH RIO MAR", "574",  "LAVDF COMERCIO FL 02", "REC"),
    # SSA
    ("ANND",            "572",  "ANND_10659",           "SSA"),
    ("FMTB",            "565",  "FMTB COMERCIO_10640",  "SSA"),
    ("LAVDF",           "571",  "LAVDF MTZ",            "SSA"),
    ("LOTTI CUCINA",    "1645", "LOTTI CUCINA",          "SSA"),
    ("LOTTI OSTERIA",  "1644", "LOTTI OSTERIA",         "SSA"),
    ("MISSKOH",         "598",  "LAVDF COMERCIO FL 01", "SSA"),
    ("RSBM",            "568",  "RSBM_10645",           "SSA"),
    ("RSTKI",           "577",  "RSTKI_10648",          "SSA"),
]


def _configurar_env(config: dict):
    """Injeta seção 'tokai' do config.json como variáveis de ambiente para o AUTO_TOKAI."""
    c = config.get("tokai", {})
    os.environ["EMAIL_USER"]          = c.get("email_user", "")
    os.environ["SHAREPOINT_BASE_URL"] = c.get("sharepoint_url", "")
    os.environ["GMAIL_LABEL"]         = c.get("gmail_label", "TOKAI - XML")
    # Só sobrescreve NETWORK_DRIVE_Z se o config.json tiver um valor não-vazio.
    # Caso contrário, o .env do auto_tokai já define o valor correto via load_dotenv().
    net_path_cfg = c.get("network_path", "").strip()
    if net_path_cfg:
        os.environ["NETWORK_DRIVE_Z"] = net_path_cfg
    os.environ["MAX_EMAIL_AGE_DAYS"]  = str(c.get("max_email_age_days", 35))
    os.environ["HEADLESS_MODE"]       = "True" if c.get("headless_mode", False) else "False"
    os.environ["DEBUG_SCREENSHOTS"]   = "False"

    # Storage state: usa caminho configurado ou padrão dentro do motor
    storage = c.get("storage_state_path", "").strip()
    if not storage:
        motor = c.get("motor_path", "").strip() or TOKAI_DIR
        storage = os.path.join(motor, "playwright_storage.json")
    os.environ["STORAGE_STATE_PATH"] = storage


def listar_clientes_tokai() -> list:
    """Retorna lista de clientes TOKAI para exibição no seletor da UI."""
    return [
        {"sp_name": sp, "codigo": cod, "nome": nome, "regiao": reg}
        for sp, cod, nome, reg in TOKAI_CLIENTS_DISPLAY
    ]


def executar_tokai(
    config: dict,
    stop_flag: threading.Event,
    progress_cb=None,
    clientes: list = None,   # None = todos; lista = filtro de unidades selecionadas
    periodo: dict = None,    # {"mes": int, "ano": int} ou None = mês anterior automático
) -> dict:
    """
    Executa o motor TOKAI (download SharePoint → Z:\\).
    Retorna {"ok": bool, "sucessos": int, "erros": int, "lista_erros": list}
    """
    def _cb(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)
        log.info(f"[{pct:3d}%] {msg}")

    if stop_flag.is_set():
        return {"ok": False, "msg": "Cancelado antes de iniciar", "sucessos": 0, "erros": 0}

    # Valida drive de rede antes de iniciar
    net_path = config.get("tokai", {}).get("network_path", "")
    if net_path:
        import os as _os
        drive, _ = _os.path.splitdrive(net_path)
        drive_root = (drive + _os.sep) if drive else _os.sep
        if not _os.path.isdir(drive_root):
            msg = f"Drive de rede inacessível: {drive_root} — configure em Config TOKAI"
            log.error(msg)
            _cb(100, msg)
            return {"ok": False, "msg": msg, "sucessos": 0, "erros": 0}

    _configurar_env(config)

    # O motor usa Playwright internamente (login SharePoint via browser). No exe
    # é preciso apontar PLAYWRIGHT_BROWSERS_PATH para o Chromium empacotado, senão
    # o launch trava/falha — mesmo motivo dos engines NF-e/NFCe/SPED.
    configurar_browsers_path()

    # O motor chama 7-Zip/unrar via subprocess para extrair os ZIPs. No exe windowed
    # cada chamada abriria uma janela CMD preta. Patch global suprime todas (motor
    # incluso) sem editar cada subprocess do motor — ver suprimir_janelas_subprocess.
    suprimir_janelas_subprocess()

    # Resolve caminho do motor (config tem precedência sobre o default)
    tokai_dir = _motor_path_efetivo(config)

    # No exe: sincroniza o código do motor para a pasta gravável antes de usar.
    try:
        _preparar_motor(tokai_dir)
    except Exception as e:
        log.warning(f"Não foi possível preparar o motor TOKAI: {e}")

    # Garante que AUTO_TOKAI está no sys.path
    if tokai_dir not in sys.path:
        sys.path.insert(0, tokai_dir)

    _cb(5, "Carregando motor TOKAI...")

    if not os.path.isdir(tokai_dir):
        msg = (f"Motor TOKAI não encontrado em '{tokai_dir}'. "
               f"Instale o auto_tokai nesta máquina ou ajuste 'motor_path' na Config TOKAI.")
        log.error(msg)
        _cb(100, msg)
        return {"ok": False, "msg": msg, "sucessos": 0, "erros": 0}

    try:
        from src.application.use_cases.download_sharepoint_files import DownloadSharePointFilesUseCase
        from src.infrastructure.email.gmail_api_service import GmailApiService
    except ModuleNotFoundError as e:
        faltante = getattr(e, "name", "") or str(e)
        if faltante and not str(faltante).startswith("src"):
            # Falta uma biblioteca Python (ex.: dateutil) — precisa entrar no exe (spec).
            msg = (f"Dependência Python ausente no executável: '{faltante}'. "
                   f"Precisa ser empacotada (hiddenimports no dmf_engine.spec).")
        else:
            # Falta o próprio motor (pasta src do auto_tokai).
            msg = (f"Motor TOKAI incompleto em '{tokai_dir}' (módulo '{faltante}'). "
                   f"Verifique a instalação do auto_tokai.")
        log.error(f"Falha ao importar motor TOKAI: {msg}")
        _cb(100, msg)
        return {"ok": False, "msg": msg, "sucessos": 0, "erros": 0}
    except Exception as e:
        msg = str(e) or f"{type(e).__name__} (sem mensagem)"
        log.error(f"Falha ao importar motor TOKAI: {msg}")
        _cb(100, f"Erro ao importar motor: {msg}")
        return {"ok": False, "msg": msg, "sucessos": 0, "erros": 0}

    if stop_flag.is_set():
        return {"ok": False, "msg": "Cancelado", "sucessos": 0, "erros": 0}

    _cb(10, "Inicializando use-case e credenciais Gmail...")

    _orig_cwd = os.getcwd()
    try:
        os.chdir(tokai_dir)
        use_case = DownloadSharePointFilesUseCase()
        # Substitui gmail_api com caminhos absolutos (evita problema de cwd)
        use_case.gmail_api = GmailApiService(
            credentials_path=os.path.join(tokai_dir, "config", "credentials.json"),
            token_path=os.path.join(tokai_dir, "config", "token.json"),
        )
    except Exception as e:
        log.error(f"Falha ao inicializar use-case TOKAI: {e}")
        _cb(100, f"Erro de inicialização: {e}")
        return {"ok": False, "msg": str(e), "sucessos": 0, "erros": 0}
    finally:
        os.chdir(_orig_cwd)

    _cb(15, "Obtendo link SharePoint via Gmail API...")

    try:
        # Usa o motor resolvido do config (não a constante default), senão o cwd
        # vai para a pasta errada quando motor_path é customizado.
        os.chdir(tokai_dir)
        # policy Proactor: o motor abre Chromium via sync_playwright e a nossa thread
        # herda a WindowsSelectorEventLoopPolicy do main.py (não cria subprocessos).
        with policy_proactor():
            resultado = use_case.execute(
                allowed_clients_override=clientes if clientes else None,
                periodo=periodo,
            )
    except BaseException as e:
        import traceback as _tb
        tb = _tb.format_exc()
        msg = str(e) or f"{type(e).__name__} (sem mensagem)"
        log.error(f"Execução TOKAI falhou: {msg}\n{tb}")
        # Grava o traceback completo num arquivo para diagnóstico (erro vem vazio na UI).
        try:
            import tempfile
            p = os.path.join(tempfile.gettempdir(), "dmf_tokai_erro.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(f"motor_path: {tokai_dir}\n\n{tb}")
            log.error(f"Detalhe do erro TOKAI salvo em: {p}")
        except Exception:
            pass
        _cb(100, f"Erro durante execução: {msg}")
        return {"ok": False, "msg": msg, "sucessos": 0, "erros": 0}
    finally:
        os.chdir(_orig_cwd)

    ok_count   = 0
    err_count  = 0
    lista_erros = []

    if resultado and len(resultado) == 3:
        ok_count, err_count, lista_erros = resultado

    _cb(100, f"Concluído — {ok_count} cliente(s) ok, {err_count} erro(s)")

    return {
        "ok":          err_count == 0,
        "sucessos":    ok_count,
        "erros":       err_count,
        "lista_erros": lista_erros or [],
    }


# ---------------------------------------------------------------------------
# Compactação local (sem re-download)
# ---------------------------------------------------------------------------

def _encontrar_7zip() -> str | None:
    for p in [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe", "7z"]:
        if os.path.isfile(p) or shutil.which(p):
            return p
    return None


def _coletar_xmls_recursivo(raiz: str, nome_zip_final: str, nome_zip_tmp: str) -> dict:
    """
    Varre raiz recursivamente e retorna um dict {nome_arquivo: caminho_absoluto_mais_recente}.
    Ignora os próprios arquivos ZIP gerados por esta rotina.
    Quando há duplicatas (mesmo nome em pastas diferentes), mantém o arquivo mais recente.
    """
    encontrados: dict[str, tuple[str, float]] = {}  # nome → (caminho_abs, mtime)
    ignorar = {os.path.basename(nome_zip_final).lower(), os.path.basename(nome_zip_tmp).lower(), "_lista_xmls.txt"}

    for dirpath, _, filenames in os.walk(raiz):
        for fname in filenames:
            if not fname.lower().endswith(".xml"):
                continue
            if fname.lower() in ignorar:
                continue
            caminho_abs = os.path.join(dirpath, fname)
            try:
                mtime = os.path.getmtime(caminho_abs)
            except OSError:
                mtime = 0.0
            chave = fname.lower()
            if chave not in encontrados or mtime > encontrados[chave][1]:
                encontrados[chave] = (caminho_abs, mtime)

    return {nome: caminho for nome, (caminho, _) in encontrados.items()}


def _compactar_pasta(caminho_final: str, data_disco: str, progress_cb=None) -> dict:
    """
    Coleta XMLs recursivamente em caminho_final (todos os níveis de subpasta),
    desduplicando por nome (mantém o mais recente), compacta em {data_disco}.zip,
    e remove todos os XMLs originais + subpastas após ZIP confirmado.
    """
    def _log(msg):
        log.info(msg)
        if progress_cb:
            progress_cb(msg)

    resultado = {"sucesso": False, "xmls_compactados": 0, "mensagem": ""}

    if not os.path.isdir(caminho_final):
        resultado["mensagem"] = f"Pasta não encontrada: {caminho_final}"
        return resultado

    nome_zip_final = os.path.join(caminho_final, f"{data_disco}.zip")
    nome_zip_tmp   = os.path.join(caminho_final, f"{data_disco}.tmp.zip")

    # Coleta recursiva com desduplicação
    xmls_map = _coletar_xmls_recursivo(caminho_final, nome_zip_final, nome_zip_tmp)

    if not xmls_map:
        resultado["mensagem"] = f"Nenhum XML encontrado em '{caminho_final}' (recursivo)"
        return resultado

    total = len(xmls_map)
    _log(f"Encontrados {total} XML(s) únicos (varredura recursiva).")

    # Conta quantos estavam em subpastas vs raiz
    em_subpasta = sum(
        1 for p in xmls_map.values()
        if os.path.dirname(p) != caminho_final
    )
    if em_subpasta:
        _log(f"  {em_subpasta} XML(s) estavam em subpastas — serão nivelados no ZIP.")

    # Se ZIP íntegro já existe, nada a fazer
    if os.path.exists(nome_zip_final):
        try:
            with zipfile.ZipFile(nome_zip_final) as zf:
                if zf.testzip() is None:
                    _log(f"ZIP já existe e está íntegro: '{os.path.basename(nome_zip_final)}' — pulando.")
                    resultado["sucesso"] = True
                    resultado["xmls_compactados"] = total
                    resultado["mensagem"] = f"ZIP já existia e íntegro ({total} XMLs)."
                    return resultado
        except Exception:
            pass
        os.remove(nome_zip_final)

    _log(f"Compactando {total} XML(s) → '{os.path.basename(nome_zip_final)}'...")

    # xmls_map: {nome_arquivo: caminho_abs} — todos vão na raiz do ZIP (sem estrutura de pastas)
    ok = False
    sz_exe = _encontrar_7zip()

    if sz_exe:
        lista_tmp = os.path.join(caminho_final, "_lista_xmls.txt")
        try:
            with open(lista_tmp, "w", encoding="utf-8") as lf:
                for caminho_abs in xmls_map.values():
                    lf.write(caminho_abs + "\n")
            # -spf- não inclui estrutura de pastas no ZIP
            cmd = [sz_exe, "a", nome_zip_tmp, f"@{lista_tmp}", "-mx=3", "-mmt", "-y", "-spf-"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            ok = proc.returncode == 0
            if not ok:
                log.warning(f"7-Zip retornou código {proc.returncode}: {proc.stderr[:200]}")
        except Exception as e:
            log.warning(f"7-Zip falhou: {e}. Tentando fallback zipfile...")
        finally:
            if os.path.exists(lista_tmp):
                os.remove(lista_tmp)

    if not ok:
        try:
            with zipfile.ZipFile(nome_zip_tmp, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                for i, (nome_arquivo, caminho_abs) in enumerate(xmls_map.items(), 1):
                    zf.write(caminho_abs, nome_arquivo)  # arcname = só o nome, sem subpasta
                    if i % 500 == 0 or i == total:
                        _log(f"  zipfile: {i}/{total} arquivos...")
            ok = True
        except Exception as e:
            resultado["mensagem"] = f"Falha na compactação (7-Zip e zipfile): {e}"
            log.error(resultado["mensagem"])
            return resultado

    # Verifica integridade antes de commitar
    try:
        with zipfile.ZipFile(nome_zip_tmp) as zf:
            bad = zf.testzip()
            if bad is not None:
                raise ValueError(f"CRC inválido em '{bad}'")
    except Exception as e:
        resultado["mensagem"] = f"ZIP temporário falhou na verificação — XMLs mantidos: {e}"
        log.error(resultado["mensagem"])
        try:
            os.remove(nome_zip_tmp)
        except Exception:
            pass
        return resultado

    os.replace(nome_zip_tmp, nome_zip_final)
    tamanho_mb = os.path.getsize(nome_zip_final) / 1024 / 1024
    _log(f"ZIP criado: '{nome_zip_final}' ({tamanho_mb:.1f} MB)")

    # Remove todos os XMLs originais (em qualquer subpasta)
    removidos = 0
    for caminho_abs in xmls_map.values():
        try:
            os.remove(caminho_abs)
            removidos += 1
        except Exception as e:
            log.warning(f"Não foi possível remover '{caminho_abs}': {e}")

    # Remove subpastas (agora vazias ou com lixo residual)
    for entry in os.scandir(caminho_final):
        if entry.is_dir():
            try:
                shutil.rmtree(entry.path)
                _log(f"Subpasta removida: '{entry.name}'")
            except Exception as e:
                log.warning(f"Não foi possível remover subpasta '{entry.name}': {e}")

    _log(f"Concluído: {removidos} XML(s) removidos, ZIP confirmado.")
    resultado["sucesso"] = True
    resultado["xmls_compactados"] = removidos
    resultado["mensagem"] = f"{removidos} XML(s) compactados em '{os.path.basename(nome_zip_final)}' ({tamanho_mb:.1f} MB)."
    return resultado


def compactar_tokai(
    config: dict,
    stop_flag: threading.Event,
    progress_cb=None,
    clientes: list = None,
    periodo: dict = None,
) -> dict:
    """
    Percorre as pastas locais dos clientes TOKAI e compacta os XMLs soltos.
    Não faz download — opera apenas sobre o que já está em Z:\\.
    """
    def _cb(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)
        log.info(f"[ZIP {pct:3d}%] {msg}")

    # Resolve caminho base
    net_path = config.get("tokai", {}).get("network_path", "").strip()
    if not net_path:
        net_path = os.environ.get("NETWORK_DRIVE_Z", "").strip().strip('"')
    if not net_path:
        msg = "Caminho de rede (NETWORK_DRIVE_Z) não configurado."
        log.error(msg)
        _cb(100, msg)
        return {"ok": False, "msg": msg, "sucessos": 0, "erros": 0, "lista_erros": [msg]}

    net_path = os.path.normpath(net_path)
    if not os.path.isdir(net_path):
        msg = f"Drive de rede inacessível: '{net_path}'"
        log.error(msg)
        _cb(100, msg)
        return {"ok": False, "msg": msg, "sucessos": 0, "erros": 0, "lista_erros": [msg]}

    # Resolve período
    if periodo and periodo.get("mes") and periodo.get("ano"):
        mes = int(periodo["mes"])
        ano = int(periodo["ano"])
    else:
        import datetime
        hoje = datetime.datetime.now()
        if hoje.month == 1:
            mes, ano = 12, hoje.year - 1
        else:
            mes, ano = hoje.month - 1, hoje.year
    data_disco = f"{mes:02d}{ano}"

    # Resolve lista de clientes
    if clientes:
        clientes_alvo = clientes
    else:
        clientes_alvo = [sp for sp, *_ in TOKAI_CLIENTS_DISPLAY]

    # Importa o mapeamento sp_name → nome_pasta_rede
    tokai_dir = _motor_path_efetivo(config)
    try:
        _preparar_motor(tokai_dir)
    except Exception:
        pass
    if tokai_dir not in sys.path:
        sys.path.insert(0, tokai_dir)
    try:
        from src.domain.config import CLIENT_MAPPING
    except Exception as e:
        log.warning(f"Não foi possível importar CLIENT_MAPPING: {e}. Usando sp_name diretamente.")
        CLIENT_MAPPING = {}

    total = len(clientes_alvo)
    ok_count = 0
    err_count = 0
    lista_erros = []

    _cb(0, f"Iniciando compactação de {total} cliente(s) — período {data_disco}...")

    for i, sp_name in enumerate(clientes_alvo, 1):
        if stop_flag.is_set():
            _cb(100, "Cancelado pelo usuário.")
            break

        pct = int((i - 1) / total * 95)
        _cb(pct, f"[{i}/{total}] {sp_name}...")

        mapping_name = CLIENT_MAPPING.get(sp_name, sp_name)
        caminho_final = os.path.join(net_path, mapping_name, data_disco)

        if not os.path.isdir(caminho_final):
            log.info(f"[{sp_name}] Pasta não existe: '{caminho_final}' — pulando.")
            continue

        def _progress_log(msg, cliente=sp_name):
            log.info(f"[{cliente}] {msg}")

        resultado = _compactar_pasta(caminho_final, data_disco, progress_cb=_progress_log)

        if resultado["sucesso"]:
            ok_count += 1
            log.info(f"[{sp_name}] OK — {resultado['mensagem']}")
        else:
            err_count += 1
            lista_erros.append(f"{sp_name}: {resultado['mensagem']}")
            log.error(f"[{sp_name}] FALHA — {resultado['mensagem']}")

    _cb(100, f"Compactação concluída — {ok_count} ok, {err_count} erro(s).")
    return {
        "ok":          err_count == 0,
        "sucessos":    ok_count,
        "erros":       err_count,
        "lista_erros": lista_erros,
    }
